"""Cliente HTTP da API BRGlobal (fonte da verdade) — somente leitura (GET).

Robusto e explícito: timeout, retries mínimos (apenas em falhas transitórias,
sobre GETs idempotentes), logs estruturados, erros tipados e degradação.

Contrato consumido: `/api/agent/v1/*` (API de agentes, read-only).
Envelope de resposta: { apiVersion, generatedAt, environment, data }.
O cliente desembrulha e devolve `data`.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx

from financebot.logging_setup import log_event


@dataclass
class FinanceAPIError(Exception):
    kind: str  # auth | scope | rate_limit | disabled | timeout | http | network | parse
    message: str
    status: int | None = None

    def __str__(self) -> str:
        return f"{self.kind}: {self.message}"


# Mensagens amigáveis por tipo de erro (degradação — exibidas ao usuário).
FRIENDLY = {
    "auth": "🔒 Falha de autenticação com a API financeira (chave inválida ou ausente).",
    "scope": "🔒 A chave do agente não tem permissão para esta consulta.",
    "rate_limit": "⏳ Muitas consultas à API agora. Tente novamente em instantes.",
    "disabled": "🚫 A API de agentes está temporariamente desabilitada.",
    "timeout": "⌛ A API financeira demorou para responder. Tente novamente.",
    "http": "⚠️ A API financeira retornou um erro. Tente novamente em instantes.",
    "network": "📡 Não consegui falar com a API financeira agora.",
    "parse": "⚠️ Resposta inesperada da API financeira.",
}


def friendly(err: FinanceAPIError) -> str:
    return FRIENDLY.get(err.kind, "⚠️ Erro ao consultar a API financeira.")


class FinanceClient:
    """Cliente assíncrono enxuto da API de agentes do BRGlobal."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
        retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._base = base_url.rstrip("/")
        self._key = api_key
        self._timeout = timeout
        self._retries = max(0, int(retries))
        self._transport = transport  # injeção p/ testes (httpx.MockTransport)

    @property
    def _headers(self) -> dict:
        h = {"Accept": "application/json", "User-Agent": "agente-financeiro/1.0"}
        if self._key:
            h["Authorization"] = f"Bearer {self._key}"
        return h

    async def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self._base}/{path.lstrip('/')}"
        attempt = 0
        last: FinanceAPIError | None = None
        while attempt <= self._retries:
            attempt += 1
            start = time.monotonic()
            try:
                async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as cli:
                    r = await cli.get(url, params=params, headers=self._headers)
                ms = int((time.monotonic() - start) * 1000)
                log_event("api_call", path=path, status=r.status_code, ms=ms, attempt=attempt)
                err = self._classify(r)
                if err is None:
                    return self._unwrap(r)
                last = err
                if self._is_retryable(err) and attempt <= self._retries:
                    await self._backoff(attempt)
                    continue
                raise err
            except httpx.TimeoutException as e:
                last = FinanceAPIError("timeout", str(e))
                log_event("api_timeout", path=path, attempt=attempt, level="warning")
            except httpx.HTTPError as e:
                last = FinanceAPIError("network", str(e))
                log_event("api_network_error", path=path, attempt=attempt, level="warning")
            # chegou aqui = exceção transitória; tenta de novo ou desiste
            if attempt <= self._retries:
                await self._backoff(attempt)
                continue
            raise last
        assert last is not None  # defensivo
        raise last

    @staticmethod
    async def _backoff(attempt: int) -> None:
        await asyncio.sleep(min(2 ** (attempt - 1), 4))

    @staticmethod
    def _is_retryable(err: FinanceAPIError) -> bool:
        """Retry só em falhas transitórias: rede/timeout/rate-limit e 5xx.
        4xx (auth/scope/404) NÃO são retentados."""
        if err.kind in ("rate_limit", "timeout", "network"):
            return True
        return err.kind == "http" and (err.status or 0) >= 500

    @staticmethod
    def _classify(r: httpx.Response) -> FinanceAPIError | None:
        code = r.status_code
        if code == 200:
            return None
        mapping = {
            401: ("auth", "não autorizado"),
            403: ("scope", "escopo insuficiente"),
            404: ("http", "endpoint não encontrado"),
            429: ("rate_limit", "rate limit atingido"),
            503: ("disabled", "api de agentes desabilitada"),
            504: ("timeout", "gateway timeout"),
        }
        kind, msg = mapping.get(code, ("http", f"http {code}"))
        return FinanceAPIError(kind, msg, code)

    @staticmethod
    def _unwrap(r: httpx.Response) -> Any:
        try:
            body = r.json()
        except ValueError as e:
            raise FinanceAPIError("parse", f"json inválido: {e}") from e
        # Envelope da API de agentes: { apiVersion, generatedAt, environment, data }
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body

    # ── Endpoints (somente leitura) ──────────────────────────────────────
    async def whoami(self) -> Any:
        return await self._get("whoami")

    async def contas_pagar_hoje(self) -> Any:
        return await self._get("contas-pagar/hoje")

    async def contas_pagar_vencidas(self) -> Any:
        return await self._get("contas-pagar/vencidas")

    async def contas_pagar_proximos(self, dias: int = 7) -> Any:
        return await self._get("contas-pagar/proximos-dias", {"dias": dias})

    async def contas_pagar_criticas(self) -> Any:
        return await self._get("contas-pagar/criticas")

    async def resumo_diario(self) -> Any:
        return await self._get("resumo-diario")

    async def painel_operacional(
        self, conta_bancaria_id: int | None = None, mes: str | None = None
    ) -> Any:
        params: dict = {}
        if conta_bancaria_id is not None:
            params["contaBancariaId"] = conta_bancaria_id
        if mes:
            params["mes"] = mes
        return await self._get("painel-operacional", params or None)
