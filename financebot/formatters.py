"""Formatação determinística (0-token) dos payloads da API → texto Telegram.

Texto puro (sem Markdown) por confiabilidade: nomes de fornecedores podem
conter `_`/`*` e quebrariam o parser de Markdown. Emojis + maiúsculas dão
hierarquia visual suficiente.

Todos os formatters são tolerantes a campos ausentes/nulos (a API pode devolver
seções `null` com `_observacoes`).
"""
from __future__ import annotations

from typing import Any

_MAX = 20


def brl(value: Any) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "R$ 0,00"
    s = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def data_br(iso: Any) -> str:
    if not isinstance(iso, str) or len(iso) < 10:
        return "—"
    p = iso[:10].split("-")
    return f"{p[2]}/{p[1]}/{p[0]}" if len(p) == 3 else iso


def _f(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _items(obj: Any) -> list:
    if isinstance(obj, dict) and isinstance(obj.get("data"), list):
        return obj["data"]
    if isinstance(obj, list):
        return obj
    return []


def _total(obj: Any, items: list) -> int:
    if isinstance(obj, dict) and isinstance(obj.get("total"), int):
        return obj["total"]
    return len(items)


def _linha_conta(c: dict) -> str:
    forn = c.get("fornecedorNome") or "(sem fornecedor)"
    base = f"• #{c.get('id', '?')} {forn} — {brl(c.get('saldoAberto'))} (vence {data_br(c.get('dataVencimento'))})"
    desc = (c.get("descricao") or "").strip()
    if desc:
        base += f"\n   {desc}"
    if c.get("dadosPagamentoPendentes"):
        base += "\n   ⚠️ sem código de pagamento (Pix/boleto)"
    return base


def lista_contas(obj: Any, titulo: str) -> str:
    items = _items(obj)
    if not items:
        return f"{titulo}\n\nNenhuma conta encontrada. ✅"
    total = _total(obj, items)
    soma = sum(_f(c.get("saldoAberto")) for c in items)
    linhas = [f"{titulo} — {total} conta(s)", ""]
    linhas += [_linha_conta(c) for c in items[:_MAX]]
    if len(items) > _MAX:
        linhas.append(f"\n… e mais {len(items) - _MAX} (mostrando {_MAX}).")
    linhas.append(f"\n💰 Total em aberto (amostra): {brl(soma)}")
    return "\n".join(linhas)


def hoje(obj: Any) -> str:
    return lista_contas(obj, "📅 CONTAS A PAGAR — HOJE")


def vencidas(obj: Any) -> str:
    return lista_contas(obj, "🔴 CONTAS VENCIDAS (em aberto)")


def proximos(obj: Any) -> str:
    return lista_contas(obj, "📆 A VENCER — PRÓXIMOS 7 DIAS")


def criticas(obj: Any) -> str:
    items = _items(obj)
    if not items:
        return "🚨 CONTAS CRÍTICAS\n\nNenhuma conta crítica no momento. ✅"
    total = _total(obj, items)
    linhas = [f"🚨 CONTAS CRÍTICAS — {total}", ""]
    for c in items[:_MAX]:
        forn = c.get("fornecedorNome") or "(sem fornecedor)"
        prio = (c.get("prioridade") or "").upper()
        tag = f" [{prio}]" if prio else ""
        linhas.append(
            f"• #{c.get('id', '?')} {forn} — {brl(c.get('saldoAberto'))} "
            f"(vence {data_br(c.get('dataVencimento'))}){tag}"
        )
        rec = (c.get("recomendacao") or "").strip()
        if rec:
            linhas.append(f"   → {rec}")
    if len(items) > _MAX:
        linhas.append(f"\n… e mais {len(items) - _MAX}.")
    return "\n".join(linhas)


def resumo(obj: Any) -> str:
    if not isinstance(obj, dict):
        return "Resumo indisponível."
    cp = obj.get("contasPagar") or {}

    def bloco(nome: str, d: Any) -> str:
        d = d or {}
        return f"  {nome}: {d.get('total', 0)} conta(s) — {brl(d.get('valorTotal'))}"

    linhas = [f"📊 RESUMO DIÁRIO ({obj.get('referencia', '')})", "", "Contas a pagar:"]
    linhas.append(bloco("Vencidas", cp.get("vencidas")))
    linhas.append(bloco("Hoje", cp.get("hoje")))
    linhas.append(bloco("Próximos 7 dias", cp.get("proximos7Dias")))
    pend = cp.get("dadosPagamentoPendentes")
    if pend is not None:
        linhas.append(f"  Sem código de pagamento: {pend}")
    return "\n".join(linhas)


def painel(obj: Any) -> str:
    if not isinstance(obj, dict):
        return "Painel indisponível."
    cp = obj.get("contasPagar") or {}
    ref = obj.get("referencia") or {}

    def bucket(nome: str, d: Any) -> str:
        d = d or {}
        return f"  {nome}: {d.get('total', 0)} — {brl(d.get('valorTotalAberto'))}"

    linhas = [f"🧭 PAINEL OPERACIONAL ({ref.get('hoje', '')})", "", "Contas a pagar:"]
    linhas.append(bucket("Vencidas", cp.get("vencidas")))
    linhas.append(bucket("Hoje", cp.get("hoje")))
    linhas.append(bucket("Próx. 7 dias", cp.get("proximos7Dias")))
    crit = cp.get("criticas") or {}
    linhas.append(f"  Críticas: {crit.get('total', 0)}")
    pend = cp.get("dadosPagamentoPendentes")
    if pend is not None:
        linhas.append(f"  Sem código de pagamento: {pend}")

    caixa = obj.get("caixa")
    if isinstance(caixa, dict):
        fecha = "fecha ✅" if caixa.get("fecha") else "NÃO fecha ⚠️"
        linhas += [
            "",
            f"Caixa: {fecha}",
            f"  Saldo final calc.: {brl(caixa.get('saldoFinal'))}",
            f"  Saldo final OFX: {brl(caixa.get('saldoFinalOfx'))}",
            f"  Diferença: {brl(caixa.get('diferenca'))}",
        ]
        sf = caixa.get("statusFechamento") or {}
        if sf:
            linhas.append(
                f"  Blockers: {sf.get('quantidadeBlockers', 0)} | fila: {sf.get('workQueueItens', 0)}"
            )

    matches = obj.get("matches") or {}
    sug = obj.get("sugestoes") or {}
    linhas += [
        "",
        f"Conciliação: matches fortes {matches.get('fortes', 0)}, "
        f"prováveis {matches.get('provaveis', 0)}; sugestões pendentes {sug.get('pendentes', 0)}",
    ]

    for o in obj.get("_observacoes") or []:
        linhas.append(f"ℹ️ {o}")
    return "\n".join(linhas)


def whoami(obj: Any) -> str:
    if not isinstance(obj, dict):
        return "whoami indisponível."
    ak = obj.get("apiKey") or {}
    esc = ", ".join(ak.get("escopos") or []) or "—"
    return (
        f"🔑 Chave: {ak.get('nome', '?')} (prefixo {ak.get('prefixo', '?')})\n"
        f"Escopos: {esc}\n"
        f"Servidor: {obj.get('serverTime', '?')}"
    )
