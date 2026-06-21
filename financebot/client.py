"""Cliente HTTP da API BRGlobal agent-ready.

Suporta os DOIS envelopes:
- legacy (endpoints antigos): recurso em `envelope.data`.
- v2 (endpoints novos): sucesso em `envelope.data.data`; erro em `envelope.error`
  (`{ok:false, errorCode, precisaConfirmar, message, candidatos, camposFaltando}`).

Chaves separadas: GET usa a chave de leitura; POST exige a chave de escrita.
Robusto: timeout, retry só em falhas transitórias, idempotência em POST, logs sem segredo.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from financebot.logging_setup import log_event

# Best-effort: usa o trust store do SO para TLS (resolve cadeias via AIA em alguns
# ambientes Windows/dev). Inofensivo na VPS Linux. Nunca enfraquece a verificação.
try:  # pragma: no cover
    import truststore as _truststore
    _truststore.inject_into_ssl()
except Exception:  # pragma: no cover
    pass

# errorCodes padronizados da API nova (seção 12 do doc agent-ready).
ERROR_CODES = {
    "AMBIGUO", "NAO_ENCONTRADO", "FALTA_CONTA_ORIGEM", "FALTA_FORMA_PAGAMENTO",
    "DUPLICADO_PROVAVEL", "EXCEDE_VALOR_COMBINADO", "SERVICO_FINALIZADO",
    "SEM_PERMISSAO", "VALIDACAO", "IDEMPOTENCY_CONFLICT", "NAO_IMPLEMENTADO",
}


@dataclass
class FinanceAPIError(Exception):
    kind: str  # auth|scope|rate_limit|disabled|timeout|http|network|parse|<errorCode>
    message: str
    status: int | None = None
    error_code: str | None = None         # errorCode da API v2, quando houver
    candidatos: list = field(default_factory=list)
    campos_faltando: list = field(default_factory=list)
    precisa_confirmar: bool = False

    def __str__(self) -> str:
        return f"{self.kind}: {self.message}"


FRIENDLY = {
    "auth": "🔒 Falha de autenticação com a API financeira (chave inválida ou ausente).",
    "scope": "🔒 A chave do agente não tem permissão (escopo) para esta operação.",
    "rate_limit": "⏳ Muitas consultas agora. Tente novamente em instantes.",
    "disabled": "🚫 A API de agentes está temporariamente desabilitada.",
    "timeout": "⌛ A API financeira demorou para responder. Tente novamente.",
    "http": "⚠️ A API financeira retornou um erro. Tente em instantes.",
    "network": "📡 Não consegui falar com a API financeira agora.",
    "parse": "⚠️ Resposta inesperada da API financeira.",
    # errorCodes v2 (mensagens amigáveis):
    "AMBIGUO": "🤔 Encontrei mais de uma opção. Qual delas?",
    "NAO_ENCONTRADO": "🔎 Não encontrei. Pode dar mais detalhes (nome completo)?",
    "FALTA_CONTA_ORIGEM": "🏦 Falta informar a conta bancária de origem.",
    "FALTA_FORMA_PAGAMENTO": "💳 Falta a forma de pagamento (pix/transferência/dinheiro/outro).",
    "DUPLICADO_PROVAVEL": "♻️ Isso parece duplicado. Confirma que quer registrar mesmo assim?",
    "EXCEDE_VALOR_COMBINADO": "💰 Valor acima do combinado. Autoriza o excedente (com motivo)?",
    "SERVICO_FINALIZADO": "🔒 O serviço está finalizado. Reabra no sistema web antes.",
    "SEM_PERMISSAO": "🔒 A chave não tem o escopo necessário para esta operação.",
    "VALIDACAO": "⚠️ Dados incompletos/ inválidos. Vou pedir o que falta.",
    "IDEMPOTENCY_CONFLICT": "⚠️ Conflito de idempotência (payload mudou). Vou revisar o rascunho.",
    "NAO_IMPLEMENTADO": "🚧 Operação não disponível pelo agente — use o sistema web.",
}

_TRANSIENT_KINDS = {"rate_limit", "timeout", "network"}


def friendly(err: FinanceAPIError) -> str:
    if err.error_code and err.error_code in FRIENDLY:
        return FRIENDLY[err.error_code]
    return FRIENDLY.get(err.kind, "⚠️ Erro ao consultar a API financeira.")


class FinanceClient:
    """Cliente assíncrono da API de agentes do BRGlobal (read + write controlada)."""

    def __init__(
        self,
        *,
        base_url: str,
        read_key: str = "",
        write_key: str = "",
        timeout: float = 32.0,
        retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._base = base_url.rstrip("/")
        self._read_key = read_key
        self._write_key = write_key
        self._timeout = timeout
        self._retries = max(0, int(retries))
        self._transport = transport  # injeção p/ testes (httpx.MockTransport)

    def _headers(self, *, write: bool, idempotency_key: str | None = None) -> dict:
        key = self._write_key if write else self._read_key
        h = {"Accept": "application/json", "User-Agent": "agente-financeiro/2.0"}
        if key:
            h["Authorization"] = f"Bearer {key}"
        if write:
            h["Content-Type"] = "application/json"
            if idempotency_key:
                h["Idempotency-Key"] = idempotency_key
        return h

    # ── Núcleo HTTP ───────────────────────────────────────────────────────
    async def _request(
        self, method: str, path: str, *, params=None, json=None,
        write: bool = False, idempotency_key: str | None = None,
    ) -> httpx.Response:
        url = f"{self._base}/{path.lstrip('/')}"
        headers = self._headers(write=write, idempotency_key=idempotency_key)
        attempt = 0
        last: FinanceAPIError | None = None
        while attempt <= self._retries:
            attempt += 1
            start = time.monotonic()
            try:
                async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as cli:
                    r = await cli.request(method, url, params=params, json=json, headers=headers)
                ms = int((time.monotonic() - start) * 1000)
                log_event("api_call", method=method, path=path, status=r.status_code,
                          ms=ms, attempt=attempt, write=write)
                # 200/201 ok; erros HTTP transitórios → retry
                if r.status_code in (200, 201):
                    return r
                err = self._classify_http(r)
                last = err
                # retry só em transitórios e nunca muda a idempotency-key
                if self._is_retryable(err) and attempt <= self._retries:
                    await self._backoff(attempt)
                    continue
                return r  # deixa o unwrap tratar erro de negócio (4xx/v2)
            except httpx.TimeoutException as e:
                last = FinanceAPIError("timeout", str(e))
                log_event("api_timeout", path=path, attempt=attempt, level="warning")
            except httpx.HTTPError as e:
                last = FinanceAPIError("network", str(e))
                log_event("api_network_error", path=path, attempt=attempt, level="warning")
            if attempt <= self._retries:
                await self._backoff(attempt)
                continue
            raise last
        assert last is not None
        raise last

    @staticmethod
    async def _backoff(attempt: int) -> None:
        await asyncio.sleep(min(2 ** (attempt - 1), 4))

    @staticmethod
    def _is_retryable(err: FinanceAPIError) -> bool:
        if err.kind in _TRANSIENT_KINDS:
            return True
        return err.kind == "http" and (err.status or 0) >= 500

    @staticmethod
    def _classify_http(r: httpx.Response) -> FinanceAPIError:
        code = r.status_code
        mapping = {
            401: ("auth", "não autorizado"),
            403: ("scope", "escopo insuficiente"),
            404: ("http", "não encontrado"),
            429: ("rate_limit", "rate limit atingido"),
            503: ("disabled", "api de agentes desabilitada"),
            504: ("timeout", "gateway timeout"),
        }
        kind, msg = mapping.get(code, ("http", f"http {code}"))
        return FinanceAPIError(kind, msg, code)

    # ── Unwrap dos 2 envelopes ────────────────────────────────────────────
    @staticmethod
    def _body(r: httpx.Response) -> dict:
        try:
            return r.json()
        except ValueError as e:
            raise FinanceAPIError("parse", f"json inválido: {e}", r.status_code) from e

    def _unwrap_legacy(self, r: httpx.Response) -> Any:
        """Endpoints antigos: recurso em envelope.data."""
        if r.status_code not in (200, 201):
            raise self._classify_http(r)
        body = self._body(r)
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body

    def _unwrap_v2(self, r: httpx.Response) -> Any:
        """Endpoints novos: sucesso em envelope.data.data; erro em envelope.error."""
        body = self._body(r)
        # erro v2 (mesmo com 4xx): envelope.error com errorCode
        err = body.get("error") if isinstance(body, dict) else None
        if isinstance(err, dict) and err.get("ok") is False:
            code = err.get("errorCode") or "VALIDACAO"
            raise FinanceAPIError(
                kind=code, message=err.get("message") or code, status=r.status_code,
                error_code=code, candidatos=err.get("candidatos") or [],
                campos_faltando=err.get("camposFaltando") or [],
                precisa_confirmar=bool(err.get("precisaConfirmar")),
            )
        if r.status_code not in (200, 201):
            raise self._classify_http(r)
        data = body.get("data") if isinstance(body, dict) else None
        # envelope.data = {ok, data, message, warnings, nextAction} → recurso em data.data
        if isinstance(data, dict) and "data" in data:
            return {"data": data.get("data"), "message": data.get("message"),
                    "warnings": data.get("warnings") or [], "nextAction": data.get("nextAction")}
        return data

    # ── Métodos públicos genéricos ────────────────────────────────────────
    async def get_legacy(self, path: str, params: dict | None = None) -> Any:
        return self._unwrap_legacy(await self._request("GET", path, params=params))

    async def get_v2(self, path: str, params: dict | None = None) -> Any:
        return self._unwrap_v2(await self._request("GET", path, params=params))

    async def post_v2(self, path: str, payload: dict, *, idempotency_key: str) -> Any:
        if not self._write_key:
            raise FinanceAPIError("scope", "chave de escrita ausente", None, error_code="SEM_PERMISSAO")
        if not idempotency_key:
            raise FinanceAPIError("validation", "idempotency-key obrigatória em POST")
        r = await self._request("POST", path, json=payload, write=True,
                                idempotency_key=idempotency_key)
        return self._unwrap_v2(r)

    # ── Endpoints ANTIGOS (legacy) — preservam os comandos atuais ─────────
    async def whoami(self) -> Any:
        return await self.get_legacy("whoami")

    async def whoami_write(self) -> Any:
        """/whoami usando a chave de ESCRITA (valida escopos write — sem POST)."""
        r = await self._request("GET", "whoami", write=True)
        return self._unwrap_legacy(r)

    async def contas_pagar_hoje(self) -> Any:
        return await self.get_legacy("contas-pagar/hoje")

    async def contas_pagar_vencidas(self) -> Any:
        return await self.get_legacy("contas-pagar/vencidas")

    async def contas_pagar_proximos(self, dias: int = 7) -> Any:
        return await self.get_legacy("contas-pagar/proximos-dias", {"dias": dias})

    async def contas_pagar_criticas(self) -> Any:
        return await self.get_legacy("contas-pagar/criticas")

    async def resumo_diario(self) -> Any:
        return await self.get_legacy("resumo-diario")

    async def painel_operacional(
        self, conta_bancaria_id: int | None = None, mes: str | None = None
    ) -> Any:
        params: dict = {}
        if conta_bancaria_id is not None:
            params["contaBancariaId"] = conta_bancaria_id
        if mes:
            params["mes"] = mes
        return await self.get_legacy("painel-operacional", params or None)
