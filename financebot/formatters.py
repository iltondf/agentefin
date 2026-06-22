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


# ── Agent-ready (v2): candidatos e pendências ─────────────────────────────
def candidatos_v2(v2: Any) -> str:
    """Resposta v2 já desembrulhada {data:{candidatos|servicos|...}}. Lista resumida."""
    d = v2.get("data") if isinstance(v2, dict) else None
    if not isinstance(d, dict):
        return "Nada encontrado."
    lista = None
    for k in ("candidatos", "servicos", "unidades", "contas"):
        if isinstance(d.get(k), list):
            lista = d[k]; break
    if not lista:
        return "Nada encontrado."
    linhas = []
    for i, c in enumerate(lista[:_MAX], 1):
        nome = c.get("nome") or c.get("apelido") or c.get("descricao") or "(sem nome)"
        extra = c.get("cargo") or c.get("tipoFornecedor") or c.get("banco") or c.get("status") or ""
        ident = c.get("id") or c.get("funcionarioId") or ""
        linhas.append(f"{i}. {nome} {('— ' + str(extra)) if extra else ''} (id {ident})".strip())
    cab = "Encontrei mais de um — qual?" if (d.get("ambiguo") or len(lista) > 1) else "Encontrado:"
    return cab + "\n" + "\n".join(linhas)


_DOMINIO_EMOJI = {"rh": "👷", "financeiro": "💸", "terceirizado": "🔧", "indefinido": "❓"}


def _resumo_draft(d) -> str:
    p = d.payload_extraido or {}
    valor = p.get("valor") or p.get("valorUnit")
    quem = p.get("nomeFuncionario") or p.get("nomeFornecedor") or p.get("nome") or ""
    desc = p.get("descricao") or p.get("tipo") or d.intent or ""
    val = f" — {brl(valor)}" if valor is not None else ""
    return f"{_DOMINIO_EMOJI.get(d.dominio, '•')} {d.dominio} — {quem} {desc}{val}".strip()


def lista_pendencias(drafts: list) -> str:
    if not drafts:
        return "Você não tem pendências. ✅"
    linhas = [f"Você tem {len(drafts)} pendência(s):", ""]
    for d in drafts:
        marca = {"confirmado": "✔", "erro": "⚠", "aguardando_confirmacao": "•"}.get(d.status, "•")
        linhas.append(f"{marca} {d.id}. {_resumo_draft(d)}  [{d.status}]")
    linhas.append("\nResponda: detalhar N · confirmar N · cancelar N")
    return "\n".join(linhas)


def resultado_write(res: Any) -> str:
    """Resumo do retorno de uma escrita (v2 {data:{...},message})."""
    if not isinstance(res, dict):
        return ""
    msg = res.get("message") or ""
    d = res.get("data") if isinstance(res.get("data"), dict) else res
    ids = []
    for k in ("lancamentoId", "contaPagarId", "servicoId", "funcionarioId", "pagamentoContaPagarId"):
        if isinstance(d, dict) and d.get(k) is not None:
            ids.append(f"{k}={d[k]}")
    warns = res.get("warnings") or []
    out = msg or (" ".join(ids))
    if ids and msg:
        out += f"\n  ({', '.join(ids)})"
    for w in warns:
        out += f"\n  ♻️ {w}"
    return out


_CAMPO_LABEL = {
    "nomeFuncionario": "Funcionário", "funcionarioId": "Funcionário (id)",
    "nomeFornecedor": "Fornecedor", "fornecedorId": "Fornecedor (id)",
    "tipo": "Tipo", "destino": "Destino", "qtd": "Quantidade", "valorUnit": "Valor unitário",
    "valor": "Valor", "data": "Data", "dataVencimento": "Vencimento", "dataPagamento": "Pago em",
    "formaPagamento": "Forma", "categoriaId": "Categoria (id)", "obraId": "Obra (id)",
    "contaBancariaId": "Conta (id)", "descricao": "Descrição",
}
_INTENT_LABEL = {
    "criar_lancamento_rh": "Lançamento RH", "criar_conta_pagar": "Conta a pagar (pendente)",
    "criar_conta_pagar_paga": "Conta paga",
}


def resumo_rascunho(d) -> str:
    """Resumo amigável de um rascunho para o usuário confirmar (mostra defaults usados)."""
    p = d.payload_extraido or {}
    linhas = [f"📝 Entendi — {_INTENT_LABEL.get(d.intent, d.intent)} (rascunho #{d.id}):", ""]
    ordem = ["nomeFuncionario", "funcionarioId", "nomeFornecedor", "fornecedorId", "tipo",
             "destino", "qtd", "valorUnit", "valor", "descricao", "data", "dataVencimento",
             "dataPagamento", "formaPagamento", "categoriaId", "obraId", "contaBancariaId"]
    for k in ordem:
        if k in p and p[k] not in (None, ""):
            v = brl(p[k]) if k in ("valor", "valorUnit") else p[k]
            linhas.append(f"  {_CAMPO_LABEL.get(k, k)}: {v}")
    usados = p.get("_defaults_usados") or []
    for u in usados:
        linhas.append(f"  ℹ️ Usei {u}")
    if d.campos_faltando:
        linhas.append(f"\n⚠️ Falta: {', '.join(d.campos_faltando)}")
    return "\n".join(linhas)


def detalhe_pendencia(d) -> str:
    p = d.payload_extraido or {}
    linhas = [f"📄 Pendência #{d.id} [{d.status}] — {d.dominio}",
              f"Intenção: {d.intent or '—'}", f"Texto: {d.texto_original}", ""]
    for k, v in p.items():
        if k.startswith("_"):  # campos internos (ex.: _defaults_usados)
            continue
        linhas.append(f"  {k}: {v}")
    if d.campos_faltando:
        linhas.append(f"\n⚠️ Faltando: {', '.join(d.campos_faltando)}")
    if d.erro_api:
        linhas.append(f"\n❌ Erro: {d.erro_api}")
    return "\n".join(linhas)


# ── Consultas financeiras (contas a pagar reais do BRGlobal) ──────────────
# Sempre começam com "Consultei o BRGlobal Financeiro." e NUNCA falam "pendências"
# (que é o domínio dos rascunhos locais do agente).
_CONSULTEI = "Consultei o BRGlobal Financeiro"

_STATUS_LABEL = {"pendente": "em aberto", "pago": "pago",
                 "parcialmente_pago": "parcialmente pago", "cancelado": "cancelado"}


def _cid(c: dict) -> Any:
    return c.get("contaPagarId") or c.get("id")


def _linha_cp(c: dict, i: int) -> str:
    forn = c.get("fornecedor") or c.get("fornecedorNome") or "(sem fornecedor)"
    st = _STATUS_LABEL.get(c.get("status"), c.get("status") or "—")
    linhas = [
        f"{i}. {forn}",
        f"   Conta ID: {_cid(c)}",
        f"   Valor: {brl(c.get('valorOriginal') if c.get('valorOriginal') is not None else c.get('valor'))}"
        f" · Saldo: {brl(c.get('saldoAberto'))}",
        f"   Vence: {data_br(c.get('dataVencimento'))} · Status: {st}",
    ]
    pg = c.get("dataPagamento")
    if pg:
        linhas.append(f"   Pago em: {data_br(pg)}")
    desc = (c.get("descricao") or "").strip()
    if desc:
        linhas.append(f"   Descrição: {desc}")
    return "\n".join(linhas)


def consulta_contas(contas: list, frase: str, total: int | None = None) -> str:
    """Lista de contas a pagar reais. `frase` descreve o recorte (ex.: 'em aberto para
    esta semana', 'vencidas', 'que vencem hoje', 'pagas')."""
    contas = contas or []
    if not contas:
        return f"{_CONSULTEI} e não encontrei contas {frase}."
    cab = f"{_CONSULTEI}. Encontrei {len(contas)} conta(s) {frase}:"
    corpo = [_linha_cp(c, i) for i, c in enumerate(contas[:_MAX], 1)]
    rodape = []
    if total is not None and total > len(contas):
        rodape.append(f"\n(há {total} no total; mostrando {len(contas)})")
    elif len(contas) > _MAX:
        rodape.append(f"\n… e mais {len(contas) - _MAX} (mostrando {_MAX}).")
    soma = sum(_f(c.get("saldoAberto")) for c in contas)
    rodape.append(f"💰 Soma dos saldos (amostra): {brl(soma)}")
    return cab + "\n\n" + "\n\n".join(corpo) + "\n" + "\n".join(rodape)


def escolher_conta(contas: list, fornecedor: str) -> str:
    cab = f"{_CONSULTEI}. Encontrei mais de uma conta da {fornecedor} em aberto. Qual delas?"
    corpo = [_linha_cp(c, i) for i, c in enumerate(contas[:_MAX], 1)]
    return cab + "\n\n" + "\n\n".join(corpo) + "\n\nResponda com o Conta ID."


def dados_pagamento(c: dict) -> str:
    """Detalhe de uma conta para pagamento. A API /buscar NÃO retorna Pix/código de
    barras/linha digitável — então informamos isso com honestidade (nunca inventar)."""
    forn = c.get("fornecedor") or "(sem fornecedor)"
    st = _STATUS_LABEL.get(c.get("status"), c.get("status") or "—")
    linhas = [f"{_CONSULTEI} — conta da {forn}:", "",
              f"  Conta ID: {_cid(c)}",
              f"  Valor: {brl(c.get('valorOriginal'))} · Saldo: {brl(c.get('saldoAberto'))}",
              f"  Vence: {data_br(c.get('dataVencimento'))} · Status: {st}"]
    if c.get("dataPagamento"):
        linhas.append(f"  Pago em: {data_br(c.get('dataPagamento'))}")
    if (c.get("descricao") or "").strip():
        linhas.append(f"  Descrição: {c['descricao'].strip()}")
    if (c.get("observacoes") or "").strip():
        linhas.append(f"  Observações: {c['observacoes'].strip()}")
    linhas.append("\n⚠️ A API não retornou Pix, código de barras ou linha digitável "
                  "cadastrados para essa conta.")
    return "\n".join(linhas)
