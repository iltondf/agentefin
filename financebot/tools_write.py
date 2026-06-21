"""Tools de ESCRITA (agent-ready) — SEMPRE confirmação humana + Idempotency-Key.

GATING (todas as 3 condições obrigatórias para chamar POST):
  1) settings.can_write  (WRITE_ENABLED=true E chave de escrita presente)
  2) rascunho confirmado pelo usuário (status 'confirmado')
  3) payload válido (schema mínimo) e sem ambiguidade pendente

Se qualquer condição faltar → NÃO chama POST (retorna ToolResult ok=False explicando).
A LLM nunca chega aqui: quem executa é o agente, após confirmação.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from financebot.client import FinanceAPIError, FinanceClient
from financebot.config import settings
from financebot.logging_setup import log_event
from financebot.tools import ToolResult


@dataclass
class WriteTool:
    name: str
    endpoint: str            # pode conter {servicoId}
    scope: str
    description: str
    build_payload: Callable[[dict], dict]
    required: tuple[str, ...]
    confirmation_required: bool = True


def gerar_idempotency_key(*, chat_id: int, draft_id: int, intent: str, ts_min: str) -> str:
    """Estável no retry do MESMO rascunho. Sem segredo. ts_min = 'YYYYMMDDHHMM'."""
    return f"tg:{chat_id}:{draft_id}:{intent}:{ts_min}"


# ── Builders de payload (a partir do payload_extraido do rascunho) ────────
def _p_lancamento_rh(p: dict) -> dict:
    out = {
        "funcionarioId": p["funcionarioId"], "tipo": p["tipo"],
        "data": p["data"], "qtd": p["qtd"], "valorUnit": p["valorUnit"],
        "observacao": p.get("observacao", ""),
    }
    for k in ("destino", "obraId", "obraUnidadeId", "servicoTabelaPrecoId", "confirmarDuplicado"):
        if p.get(k) is not None:
            out[k] = p[k]
    return out


def _p_conta_pagar(p: dict) -> dict:
    out = {
        "fornecedorId": p["fornecedorId"], "categoriaId": p["categoriaId"],
        "descricao": p["descricao"], "valor": p["valor"],
        "dataVencimento": p["dataVencimento"], "pago": bool(p.get("pago", False)),
        "observacoes": p.get("observacoes", ""),
    }
    for k in ("obraId", "obraUnidadeId", "dataCompetencia", "contaBancariaId",
              "formaPagamento", "dataPagamento", "confirmarDuplicado"):
        if p.get(k) is not None:
            out[k] = p[k]
    return out


def _p_pagamento_servico(p: dict) -> dict:
    out = {
        "valor": p["valor"], "dataPagamento": p["dataPagamento"], "tipo": p["tipo"],
        "formaPagamento": p["formaPagamento"], "contaBancariaId": p["contaBancariaId"],
        "observacao": p.get("observacao", ""),
    }
    for k in ("excedenteAutorizado", "motivoExcedente", "confirmarDuplicado"):
        if p.get(k) is not None:
            out[k] = p[k]
    return out


def _p_servico_terc(p: dict) -> dict:
    out = {
        "funcionarioId": p["funcionarioId"], "descricao": p["descricao"],
        "valorCombinado": p["valorCombinado"], "obraId": p["obraId"],
        "observacoes": p.get("observacoes", ""),
    }
    for k in ("obraUnidadeIds", "dataInicio", "dataPrevisaoFim", "confirmarDuplicado"):
        if p.get(k) is not None:
            out[k] = p[k]
    return out


def _p_cadastrar_terc(p: dict) -> dict:
    out = {"nome": p["nome"], "funcao": p["funcao"]}
    for k in ("cpfCnpj", "telefone", "chavePix", "obraDefaultId", "confirmarDuplicado"):
        if p.get(k) is not None:
            out[k] = p[k]
    return out


WRITE_TOOLS: dict[str, WriteTool] = {
    "criar_lancamento_rh": WriteTool(
        "criar_lancamento_rh", "rh/lancamentos", "write:rh",
        "Cria lançamento RH (diária/tarefa/adiantamento/ajuste/falta/inss)",
        _p_lancamento_rh, ("funcionarioId", "tipo", "data", "qtd", "valorUnit")),
    "criar_conta_pagar": WriteTool(
        "criar_conta_pagar", "financeiro/contas-pagar", "write:financeiro",
        "Cria conta a pagar (pendente)", _p_conta_pagar,
        ("fornecedorId", "categoriaId", "descricao", "valor", "dataVencimento")),
    "criar_conta_pagar_paga": WriteTool(
        "criar_conta_pagar_paga", "financeiro/contas-pagar", "write:financeiro",
        "Cria conta a pagar já paga (cria CP + baixa)", _p_conta_pagar,
        ("fornecedorId", "categoriaId", "descricao", "valor", "dataVencimento",
         "contaBancariaId", "formaPagamento", "dataPagamento")),
    "registrar_pagamento_servico_terceirizado": WriteTool(
        "registrar_pagamento_servico_terceirizado",
        "terceirizados/servicos/{servicoId}/pagamentos", "write:terceirizados",
        "Registra pagamento de serviço terceirizado (CP paga + baixa)", _p_pagamento_servico,
        ("servicoId", "valor", "dataPagamento", "tipo", "formaPagamento", "contaBancariaId")),
    "criar_servico_terceirizado": WriteTool(
        "criar_servico_terceirizado", "terceirizados/servicos", "write:terceirizados",
        "Cria serviço de terceirizado", _p_servico_terc,
        ("funcionarioId", "descricao", "valorCombinado", "obraId")),
    "cadastrar_terceirizado": WriteTool(
        "cadastrar_terceirizado", "terceirizados", "write:terceirizados|write:cadastros_basico",
        "Cadastra terceirizado rápido", _p_cadastrar_terc, ("nome", "funcao")),
}


def validar_payload(tool: WriteTool, payload: dict) -> list[str]:
    """Retorna lista de campos obrigatórios faltando (vazia = ok)."""
    faltando = [c for c in tool.required if payload.get(c) in (None, "")]
    # validações determinísticas extra
    if payload.get("valor") is not None and not _num_pos(payload["valor"]):
        faltando.append("valor>0")
    if payload.get("valorUnit") is not None and not _num_pos(payload["valorUnit"]):
        faltando.append("valorUnit>0")
    if payload.get("destino") not in (None, "vale", "pagamento") and tool.name == "criar_lancamento_rh":
        faltando.append("destino(vale|pagamento)")
    return faltando


def _num_pos(v: Any) -> bool:
    try:
        return float(v) > 0
    except (TypeError, ValueError):
        return False


async def executar_write(
    client: FinanceClient, *, intent: str, draft, idempotency_key: str,
) -> ToolResult:
    """Executa a tool de escrita SOMENTE se o gating permitir. `draft` é um Draft confirmado."""
    tool = WRITE_TOOLS.get(intent)
    if not tool:
        return ToolResult(False, error_kind="intent", text=f"tool de escrita desconhecida: {intent}")

    # Gate 1 — escrita habilitada + chave
    if not settings.can_write:
        motivo = "WRITE_ENABLED=false" if not settings.write_enabled else "chave de escrita ausente"
        log_event("write_bloqueado", intent=intent, motivo=motivo, level="warning")
        return ToolResult(False, error_kind="disabled",
                          text=f"✍️ Escrita desabilitada ({motivo}). Rascunho mantido para confirmar depois.")
    # Gate 2 — rascunho confirmado
    if getattr(draft, "status", None) != "confirmado":
        return ToolResult(False, error_kind="confirm",
                          text="Confirmação humana necessária antes de gravar.")
    # Gate 3 — payload válido
    payload = tool.build_payload(draft.payload_extraido)
    faltando = validar_payload(tool, payload)
    if faltando:
        return ToolResult(False, error_kind="VALIDACAO",
                          text=f"Faltam dados: {', '.join(faltando)}")

    endpoint = tool.endpoint
    if "{servicoId}" in endpoint:
        endpoint = endpoint.replace("{servicoId}", str(draft.payload_extraido["servicoId"]))

    try:
        res = await client.post_v2(endpoint, payload, idempotency_key=idempotency_key)
        log_event("write_ok", intent=intent, idem=idempotency_key)
        return ToolResult(True, data=res, text="✅ Registrado.")
    except FinanceAPIError as e:
        log_event("write_erro", intent=intent, kind=e.kind, code=e.error_code, level="warning")
        return ToolResult(False, data={"erro": str(e), "candidatos": e.candidatos,
                                       "campos_faltando": e.campos_faltando,
                                       "precisa_confirmar": e.precisa_confirmar},
                          error_kind=e.error_code or e.kind, text=str(e))
