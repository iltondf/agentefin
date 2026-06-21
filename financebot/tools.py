"""Registry de tools — camada única usada por comandos manuais E pela LLM.

Sem framework (sem LangChain/CrewAI/etc.). Uma Tool é um objeto simples:
- read tools: chamam GET (legacy ou v2) e formatam.
- write tools: ver tools_write.py (exigem confirmação + Idempotency-Key + gating).

A LLM nunca executa: ela apenas escolhe `name` + monta `args`; o agente roda `run`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from financebot.client import FinanceClient


@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    text: str = ""
    error_kind: str | None = None


@dataclass
class Tool:
    name: str
    kind: str  # "read" | "write"
    description: str
    scope: str
    run: Callable[..., Awaitable[ToolResult]]
    args_schema: dict = field(default_factory=dict)
    confirmation_required: bool = False


# ── Helpers de extração (envelopes já desembrulhados pelo client) ─────────
def _candidatos(v2: Any) -> list:
    """Para respostas v2 {data:{...}}: tenta achar a lista de candidatos comum."""
    d = v2.get("data") if isinstance(v2, dict) else None
    if isinstance(d, dict):
        for k in ("candidatos", "servicos", "unidades", "contas"):
            if isinstance(d.get(k), list):
                return d[k]
    if isinstance(d, list):
        return d
    return []


def build_read_registry(client: FinanceClient) -> dict[str, Tool]:
    """Tools de LEITURA: antigas (legacy) + novas (v2). Sem confirmação."""

    # ── Antigas (legacy) — preservam os comandos atuais ──
    async def _whoami(_a):       return ToolResult(True, await client.whoami())
    async def _hoje(_a):         return ToolResult(True, await client.contas_pagar_hoje())
    async def _vencidas(_a):     return ToolResult(True, await client.contas_pagar_vencidas())
    async def _criticas(_a):     return ToolResult(True, await client.contas_pagar_criticas())
    async def _resumo(_a):       return ToolResult(True, await client.resumo_diario())
    async def _proximos(a):      return ToolResult(True, await client.contas_pagar_proximos(int(a.get("dias", 7))))
    async def _painel(a):        return ToolResult(True, await client.painel_operacional(a.get("contaBancariaId"), a.get("mes")))

    # ── Novas (v2) GET de resolução/busca ──
    async def _buscar_func(a):   return ToolResult(True, await client.get_v2("rh/funcionarios/buscar", {"nome": a["nome"]}))
    async def _buscar_forn(a):   return ToolResult(True, await client.get_v2("financeiro/fornecedores/buscar", {"nome": a["nome"]}))
    async def _buscar_obra(a):   return ToolResult(True, await client.get_v2("cadastros/obras/buscar", {"nome": a["nome"]}))
    async def _buscar_unid(a):   return ToolResult(True, await client.get_v2(f"cadastros/obras/{int(a['obraId'])}/unidades"))
    async def _buscar_terc(a):   return ToolResult(True, await client.get_v2("terceirizados/buscar", {"nome": a["nome"]}))
    async def _buscar_serv(a):   return ToolResult(True, await client.get_v2("terceirizados/servicos/buscar", {k: v for k, v in a.items() if k in ("nome", "status")}))
    async def _detalhar_serv(a): return ToolResult(True, await client.get_v2(f"terceirizados/servicos/{int(a['id'])}"))
    async def _buscar_contas_b(a):
        if a.get("nome"):
            return ToolResult(True, await client.get_v2("financeiro/contas-bancarias/buscar", {"nome": a["nome"]}))
        return ToolResult(True, await client.get_v2("financeiro/contas-bancarias"))
    async def _fechamento_rh(a):
        if a.get("funcionarioId"):
            return ToolResult(True, await client.get_v2("rh/fechamento/funcionario", {k: a[k] for k in ("funcionarioId", "mes", "tipo") if k in a}))
        return ToolResult(True, await client.get_v2("rh/fechamento", {k: a[k] for k in ("mes", "tipo") if k in a}))
    async def _resumo_rh(a):     return ToolResult(True, await client.get_v2("rh/resumo", {"funcionarioId": a["funcionarioId"], "mes": a["mes"]}))
    async def _extrato_rh(a):    return ToolResult(True, await client.get_v2("rh/extrato", {"funcionarioId": a["funcionarioId"], "mes": a["mes"]}))
    async def _buscar_pix(a):    return ToolResult(True, await client.get_v2("extrato/pix/buscar", {k: v for k, v in a.items() if k in ("valor", "data", "nome", "contaBancariaId")}))
    async def _buscar_extr(a):   return ToolResult(True, await client.get_v2("extrato/buscar", {k: v for k, v in a.items() if k in ("valor", "data", "contaBancariaId")}))
    async def _buscar_cp(a):     return ToolResult(True, await client.get_v2("financeiro/contas-pagar/buscar", {k: v for k, v in a.items() if k in ("fornecedor", "status", "obraId")}))

    tools = [
        # legacy
        Tool("consultar_whoami", "read", "Diagnóstico da chave do agente", "(Bearer)", _whoami),
        Tool("consultar_contas_hoje", "read", "Contas a pagar que vencem hoje", "read:financeiro", _hoje),
        Tool("consultar_contas_vencidas", "read", "Contas vencidas em aberto", "read:financeiro", _vencidas),
        Tool("consultar_contas_criticas", "read", "Contas críticas (prioridade alta)", "read:financeiro", _criticas),
        Tool("consultar_contas_proximos_dias", "read", "A vencer nos próximos N dias", "read:financeiro", _proximos, {"dias": "int 1-90"}),
        Tool("consultar_resumo_diario", "read", "Resumo diário", "read:financeiro", _resumo),
        Tool("consultar_painel_operacional", "read", "Painel operacional consolidado", "read:financeiro", _painel, {"contaBancariaId": "int?", "mes": "YYYY-MM?"}),
        # novas v2
        Tool("buscar_funcionarios", "read", "Busca funcionário por nome", "read:rh", _buscar_func, {"nome": "str"}),
        Tool("buscar_fornecedores", "read", "Busca fornecedor por nome", "read:financeiro", _buscar_forn, {"nome": "str"}),
        Tool("buscar_obras", "read", "Busca obra por nome", "read:cadastros", _buscar_obra, {"nome": "str"}),
        Tool("buscar_unidades", "read", "Unidades de uma obra", "read:cadastros", _buscar_unid, {"obraId": "int"}),
        Tool("buscar_terceirizados", "read", "Busca terceirizado por nome", "read:terceirizados", _buscar_terc, {"nome": "str"}),
        Tool("buscar_servicos_terceirizado", "read", "Busca serviços por nome do terceirizado", "read:terceirizados", _buscar_serv, {"nome": "str", "status": "str?"}),
        Tool("detalhar_servico_terceirizado", "read", "Detalhe de um serviço (saldo/pagamentos)", "read:terceirizados", _detalhar_serv, {"id": "int"}),
        Tool("buscar_contas_bancarias", "read", "Lista/busca contas bancárias (sanitizado)", "read:financeiro", _buscar_contas_b, {"nome": "str?"}),
        Tool("consultar_fechamento_rh", "read", "Preview de fechamento RH", "read:rh", _fechamento_rh, {"mes": "YYYY-MM", "tipo": "vale|pagamento", "funcionarioId": "int?"}),
        Tool("consultar_resumo_rh", "read", "Lançamentos do mês do funcionário", "read:rh", _resumo_rh, {"funcionarioId": "int", "mes": "YYYY-MM"}),
        Tool("consultar_extrato_rh", "read", "Extrato do mês do funcionário", "read:rh", _extrato_rh, {"funcionarioId": "int", "mes": "YYYY-MM"}),
        Tool("buscar_pix", "read", "Pix candidatos por valor/data/nome", "read:extrato", _buscar_pix, {"valor": "num?", "data": "YYYY-MM-DD?", "nome": "str?"}),
        Tool("buscar_extrato", "read", "Transações bancárias candidatas", "read:extrato", _buscar_extr, {"valor": "num?", "data": "YYYY-MM-DD?"}),
        Tool("buscar_contas_pagar", "read", "Resolve conta a pagar por fornecedor/filtro", "read:financeiro", _buscar_cp, {"fornecedor": "str?", "status": "str?", "obraId": "int?"}),
    ]
    return {t.name: t for t in tools}


# nomes expostos (para a LLM escolher e para validação de whitelist)
def read_tool_names(registry: dict[str, Tool]) -> list[str]:
    return [n for n, t in registry.items() if t.kind == "read"]
