"""Resolução determinística de rascunho → payload pronto para escrita.

Transforma campos "humanos" do rascunho (nomeFuncionario, nomeFornecedor, datas
relativas) em IDs reais (via tools de busca) e aplica defaults (obra/conta/categoria/
forma/data). NUNCA inventa ID: se a busca for ambígua/vazia, devolve pergunta.

Retorna (payload, faltando, pergunta):
- payload: dict pronto para tools_write (ou parcial)
- faltando: lista de campos ainda ausentes
- pergunta: str para o usuário (ambiguidade/campo crítico) ou None
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from financebot import defaults
from financebot.client import FinanceAPIError, FinanceClient


def _hoje() -> str:
    return date.today().isoformat()


def _amanha() -> str:
    return (date.today() + timedelta(days=1)).isoformat()


def normalizar_data(v: Any) -> str:
    s = str(v or "").strip().lower()
    if s in ("", "hoje", "today"):
        return _hoje()
    if s in ("amanha", "amanhã", "tomorrow"):
        return _amanha()
    return str(v)


def _cands(v2: Any) -> list:
    d = v2.get("data") if isinstance(v2, dict) else None
    if isinstance(d, dict):
        for k in ("candidatos",):
            if isinstance(d.get(k), list):
                return d[k]
    return []


async def _resolver_unico(client: FinanceClient, path: str, nome: str, rotulo: str):
    """Retorna (id, erro|None). Ambíguo/vazio → (None, pergunta)."""
    try:
        res = await client.get_v2(path, {"nome": nome})
    except FinanceAPIError as e:
        return None, f"Erro ao buscar {rotulo}: {e.message}"
    cands = _cands(res)
    if not cands:
        return None, f"Não encontrei {rotulo} '{nome}'. Confira o nome."
    if len(cands) > 1:
        nomes = ", ".join(f"{c.get('nome')}(id {c.get('id') or c.get('funcionarioId')})" for c in cands[:8])
        return None, f"Há mais de um {rotulo} para '{nome}': {nomes}. Qual o id?"
    c = cands[0]
    return (c.get("id") or c.get("funcionarioId")), None


async def resolver(client: FinanceClient, draft) -> tuple[dict, list, str | None]:
    intent = draft.intent or ""
    p = dict(draft.payload_extraido or {})

    if intent == "criar_lancamento_rh":
        return await _rh(client, p)
    if intent in ("criar_conta_pagar", "criar_conta_pagar_paga"):
        return await _cp(client, p, paga=(intent == "criar_conta_pagar_paga"))
    return p, [], None  # intents sem resolução específica


async def _rh(client: FinanceClient, p: dict) -> tuple[dict, list, str | None]:
    out: dict = {}
    # funcionário: id explícito ou por nome
    if p.get("funcionarioId"):
        out["funcionarioId"] = int(p["funcionarioId"])
    elif p.get("nomeFuncionario"):
        fid, err = await _resolver_unico(client, "rh/funcionarios/buscar", p["nomeFuncionario"], "funcionário")
        if err:
            return out, ["funcionarioId"], err
        out["funcionarioId"] = fid
    else:
        return out, ["funcionarioId"], "Para qual funcionário?"

    out["tipo"] = p.get("tipo") or "ajuste_positivo"
    out["data"] = normalizar_data(p.get("data"))
    out["qtd"] = p.get("qtd", 1)
    out["valorUnit"] = p.get("valorUnit", p.get("valor"))
    if p.get("destino"):
        out["destino"] = p["destino"]
    else:
        dest = defaults.get("rh.destinoPadrao")
        if dest:
            out["destino"] = dest
    if p.get("observacao"):
        out["observacao"] = p["observacao"]

    faltando = [k for k in ("funcionarioId", "tipo", "data", "valorUnit") if out.get(k) in (None, "")]
    if not out.get("destino"):
        return out, faltando + ["destino"], "Isso vai para VALE ou PAGAMENTO?"
    return out, faltando, None


async def _cp(client: FinanceClient, p: dict, *, paga: bool) -> tuple[dict, list, str | None]:
    out: dict = {"pago": paga}
    usados: list[str] = []  # defaults aplicados (mostrar no resumo)
    # ── Fornecedor ──
    if p.get("fornecedorId"):
        out["fornecedorId"] = int(p["fornecedorId"])
    elif p.get("nomeFornecedor"):
        try:
            res = await client.get_v2("financeiro/fornecedores/buscar", {"nome": p["nomeFornecedor"]})
        except FinanceAPIError as e:
            return out, ["fornecedorId"], f"Erro ao buscar fornecedor: {e.message}"
        cands = _cands(res)
        if len(cands) == 1:
            out["fornecedorId"] = cands[0].get("id")
        elif len(cands) > 1:
            nomes = ", ".join(f"{c.get('nome')}(id {c.get('id')})" for c in cands[:8])
            return out, ["fornecedorId"], (
                f"Encontrei mais de um fornecedor parecido com '{p['nomeFornecedor']}': {nomes}. "
                "Qual o id? (ou diga 'outros' para lançar sem fornecedor definido)")
        else:
            # Nenhum parecido → lança em "Outros" e marca para ajuste depois.
            fid_outros = defaults.get("fornecedorOutrosId")
            if fid_outros:
                out["fornecedorId"] = fid_outros
                tag = f"[AJUSTAR FORNECEDOR: {p['nomeFornecedor']}]"
                out["observacoes"] = f"{tag} {p.get('observacoes','')}".strip()
                usados.append(f"fornecedor não encontrado → lançado em Outros ({tag})")
            else:
                return out, ["fornecedorId"], (
                    f"Não encontrei o fornecedor '{p['nomeFornecedor']}' e não há fornecedor "
                    "'Outros' configurado. Informe o id do fornecedor ou cadastre-o no sistema web.")
    else:
        return out, ["fornecedorId"], "De qual fornecedor?"

    # ── Categoria: explícita → palavra-chave → categoria padrão (nunca pergunta) ──
    if p.get("categoriaId"):
        out["categoriaId"] = p["categoriaId"]
    else:
        termo = f"{p.get('categoriaPalavra','')} {p.get('descricao','')} {p.get('texto','')}"
        cat = defaults.categoria_por_palavra(termo)
        if cat:
            out["categoriaId"] = cat
            usados.append(f"categoria provável: {cat}")
        elif defaults.get("categoriaPadraoId"):
            out["categoriaId"] = defaults.get("categoriaPadraoId")
            usados.append(f"categoria padrão: {defaults.get('categoriaPadraoId')}")
    # obra default (opcional)
    if p.get("obraId"):
        out["obraId"] = p["obraId"]
    elif defaults.get("obraPadraoId"):
        out["obraId"] = defaults.get("obraPadraoId")
        usados.append(f"obra padrão: {defaults.get('obraPadraoId')}")

    out["descricao"] = p.get("descricao") or "conta via agente"
    out["valor"] = p.get("valor", p.get("valorUnit"))
    out["dataVencimento"] = normalizar_data(p.get("dataVencimento") or ("hoje" if paga else "amanha"))
    # preserva tag [AJUSTAR FORNECEDOR] já posta em out["observacoes"], se houver
    if p.get("observacoes"):
        out["observacoes"] = f"{out.get('observacoes','')} {p['observacoes']}".strip()

    if paga:
        if p.get("formaPagamento"):
            out["formaPagamento"] = p["formaPagamento"]
        else:
            out["formaPagamento"] = defaults.get("formaPagamentoPadrao") or "pix"
            usados.append(f"forma de pagamento: {out['formaPagamento']}")
        out["dataPagamento"] = normalizar_data(p.get("dataPagamento") or "hoje")
        # ── Conta bancária de saída: id → alias (conta1/conta2) → final (85/97) → padrão ──
        conta_id = None
        if p.get("contaBancariaId"):
            conta_id = p["contaBancariaId"]
        elif p.get("contaBancariaAlias"):
            conta_id = defaults.conta_por_alias(p["contaBancariaAlias"])
        if conta_id is None and p.get("contaBancariaFinal"):
            conta_id = defaults.conta_por_final(p["contaBancariaFinal"])
        if conta_id is not None:
            out["contaBancariaId"] = conta_id
            ref = p.get("contaBancariaAlias") or (("final " + str(p["contaBancariaFinal"])) if p.get("contaBancariaFinal") else "")
            if ref:
                usados.append(f"conta informada ({ref}) → id {conta_id}")
        elif (p.get("contaBancariaAlias") or p.get("contaBancariaFinal")):
            # usuário citou uma conta que não casou com nenhum alias/final → perguntar
            out["_defaults_usados"] = usados
            return out, ["contaBancariaId"], (
                "Não reconheci a conta que você citou. Qual conta? (ex.: conta 1 / final 85, "
                "conta 2 / final 97)")
        elif defaults.get("contaBancariaPadraoId"):
            out["contaBancariaId"] = defaults.get("contaBancariaPadraoId")
            usados.append(f"conta padrão (id {defaults.get('contaBancariaPadraoId')})")
    out["_defaults_usados"] = usados

    req = ["fornecedorId", "categoriaId", "valor", "dataVencimento"]
    if paga:
        req += ["contaBancariaId", "formaPagamento", "dataPagamento"]
    faltando = [k for k in req if out.get(k) in (None, "")]
    pergunta = None
    if "categoriaId" in faltando:
        pergunta = "Qual a categoria? (informe o id ou configure defaults.yaml)"
    elif "contaBancariaId" in faltando:
        pergunta = "De qual conta bancária saiu o pagamento? (informe o id)"
    return out, faltando, pergunta
