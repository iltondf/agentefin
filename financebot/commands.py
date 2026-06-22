"""Command Router — comandos antigos (0 token) + read tools + pendências + escrita.

Fluxo de escrita (sempre): mensagem/comando → RASCUNHO → resumo → `confirmar N`
→ resolve IDs (busca) → valida → POST (Idempotency-Key) → resultado. Gating em tools_write.
A LLM (se ligada) é parser; comandos manuais funcionam mesmo com LLM desligada.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from financebot import defaults
from financebot import formatters as fmt
from financebot import parser, resolve
from financebot.client import FinanceAPIError, FinanceClient, friendly
from financebot.config import Settings
from financebot.logging_setup import log_event
from financebot.tools import build_read_registry
from financebot.tools_write import WRITE_TOOLS, executar_write, gerar_idempotency_key, validar_payload

HELP = (
    "Agente Financeiro BRGlobal 🤖💰\n"
    "Consultas (somente leitura):\n"
    "/hoje /vencidas /criticas /proximos7 /painel /resumo /whoami\n\n"
    "Buscas:\n"
    "/buscar_funcionario <nome> · /buscar_fornecedor <nome> · /buscar_conta <nome>\n\n"
    "Lançar (cria rascunho — confirma depois):\n"
    "/rh_teste <funcionario> <tipo> <vale|pagamento> <valor> [hoje]\n"
    "/cp_teste <fornecedor> <valor> [amanha]\n"
    "/conta_paga_teste <fornecedor> <valor> [pix] [hoje]\n"
    "ou frase natural (se LLM ligada): \"Edson ajuste positivo R$1 no pagamento\"\n\n"
    "Pendências:\n"
    "/pendencias · detalhar N · confirmar N · cancelar N · corrigir N <campo> <valor>\n\n"
    "/ajuda — esta ajuda"
)


def build_router(client: FinanceClient, settings: Settings, store=None) -> Router:
    router = Router()
    read_tools = build_read_registry(client)

    async def run_query(message: Message, coro_factory, formatter) -> None:
        try:
            data = await coro_factory()
        except FinanceAPIError as e:
            log_event("cmd_erro", kind=e.kind, status=e.status, level="warning")
            await message.answer(friendly(e)); return
        except Exception:
            log_event("cmd_excecao", level="error")
            await message.answer("⚠️ Erro inesperado ao consultar a API financeira."); return
        try:
            await message.answer(formatter(data))
        except Exception:
            log_event("fmt_excecao", level="error")
            await message.answer("⚠️ Não consegui formatar a resposta da API.")

    def _need_store(m: Message) -> bool:
        if not store or not store.available:
            return False
        return True

    # ── Comandos antigos (inalterados) ──
    @router.message(CommandStart())
    async def _start(m: Message): await m.answer(HELP)

    @router.message(Command("ajuda", "help"))
    async def _ajuda(m: Message): await m.answer(HELP)

    @router.message(Command("hoje"))
    async def _hoje(m: Message): await run_query(m, client.contas_pagar_hoje, fmt.hoje)

    @router.message(Command("vencidas"))
    async def _venc(m: Message): await run_query(m, client.contas_pagar_vencidas, fmt.vencidas)

    @router.message(Command("criticas"))
    async def _crit(m: Message): await run_query(m, client.contas_pagar_criticas, fmt.criticas)

    @router.message(Command("proximos7"))
    async def _prox(m: Message): await run_query(m, lambda: client.contas_pagar_proximos(7), fmt.proximos)

    @router.message(Command("painel"))
    async def _painel(m: Message):
        cid = settings.default_conta_bancaria_id
        await run_query(m, lambda: client.painel_operacional(conta_bancaria_id=cid), fmt.painel)

    @router.message(Command("resumo"))
    async def _resumo(m: Message): await run_query(m, client.resumo_diario, fmt.resumo)

    @router.message(Command("whoami"))
    async def _whoami(m: Message): await run_query(m, client.whoami, fmt.whoami)

    # ── Buscas ──
    async def _busca(m: Message, tool_name: str):
        termo = (m.text or "").split(maxsplit=1)
        if len(termo) < 2:
            await m.answer("Uso: informe um nome. Ex.: /buscar_fornecedor Condor"); return
        try:
            res = await read_tools[tool_name].run({"nome": termo[1].strip()})
        except FinanceAPIError as e:
            await m.answer(friendly(e)); return
        except Exception:
            await m.answer("⚠️ Erro na busca."); return
        await m.answer(fmt.candidatos_v2(res.data))

    @router.message(Command("buscar_funcionario"))
    async def _bf(m: Message): await _busca(m, "buscar_funcionarios")

    @router.message(Command("buscar_fornecedor"))
    async def _bfor(m: Message): await _busca(m, "buscar_fornecedores")

    @router.message(Command("buscar_conta"))
    async def _bc(m: Message): await _busca(m, "buscar_contas_bancarias")

    # ── Criação manual de rascunho (fallback sem LLM) ──
    async def _criar_rascunho(m: Message, intent: str, dominio: str, payload: dict):
        if not _need_store(m):
            await m.answer("⚠️ Rascunhos indisponíveis (sem persistência). Configure DATA_DIR/volume."); return
        d = store.create(chat_id=m.chat.id, user_id=m.from_user.id, texto=m.text or "",
                         dominio=dominio, intent=intent, payload=payload, faltando=[])
        await m.answer(fmt.detalhe_pendencia(d) +
                       f"\n\nConfirme: confirmar {d.id}  |  cancelar {d.id}  |  corrigir {d.id} <campo> <valor>")

    @router.message(Command("rh_teste"))
    async def _rh_teste(m: Message):
        # /rh_teste <funcionario> <tipo> <vale|pagamento> <valor> [data]
        a = (m.text or "").split()
        if len(a) < 5:
            await m.answer("Uso: /rh_teste <funcionario> <tipo> <vale|pagamento> <valor> [hoje]"); return
        payload = {"nomeFuncionario": a[1], "tipo": a[2], "destino": a[3], "valorUnit": a[4],
                   "qtd": 1, "data": (a[5] if len(a) > 5 else "hoje"),
                   "observacao": "[TESTE_AGENT_READY] Lancamento RH de teste via agente"}
        await _criar_rascunho(m, "criar_lancamento_rh", "rh", payload)

    @router.message(Command("cp_teste"))
    async def _cp_teste(m: Message):
        # /cp_teste <fornecedor> <valor> [data]
        a = (m.text or "").split()
        if len(a) < 3:
            await m.answer("Uso: /cp_teste <fornecedor> <valor> [amanha]"); return
        payload = {"nomeFornecedor": a[1], "valor": a[2], "dataVencimento": (a[3] if len(a) > 3 else "amanha"),
                   "descricao": "[TESTE_AGENT_READY] Conta de teste agent-ready",
                   "observacoes": "[TESTE_AGENT_READY] Criada por teste controlado do agente"}
        await _criar_rascunho(m, "criar_conta_pagar", "financeiro", payload)

    @router.message(Command("conta_paga_teste"))
    async def _cpp_teste(m: Message):
        # /conta_paga_teste <fornecedor> <valor> [pix] [data]
        a = (m.text or "").split()
        if len(a) < 3:
            await m.answer("Uso: /conta_paga_teste <fornecedor> <valor> [pix] [hoje]"); return
        payload = {"nomeFornecedor": a[1], "valor": a[2],
                   "formaPagamento": (a[3] if len(a) > 3 else "pix"),
                   "dataPagamento": (a[4] if len(a) > 4 else "hoje"), "dataVencimento": "hoje",
                   "descricao": "[TESTE_AGENT_READY] Conta paga de teste agent-ready",
                   "observacoes": "[TESTE_AGENT_READY] Criada/paga por teste controlado do agente"}
        await _criar_rascunho(m, "criar_conta_pagar_paga", "financeiro", payload)

    # ── Pendências ──
    @router.message(Command("pendencias"))
    async def _pend(m: Message):
        if not _need_store(m):
            await m.answer("⚠️ Rascunhos indisponíveis (sem persistência)."); return
        store.expire_old()
        await m.answer(fmt.lista_pendencias(store.list_active(m.from_user.id)))

    # ── Texto livre (mensagens de pendência + parser LLM) ──
    @router.message()
    async def _freeform(m: Message):
        texto = (m.text or "").strip()
        log_event("freeform_in", uid=getattr(m.from_user, "id", None),
                  has_text=bool(texto), llm=parser.is_enabled())
        try:
            if store and store.available:
                if await _maybe_pendencia_cmd(m, store, client, settings, texto.lower()):
                    return
            # Consulta financeira REAL (contas a pagar) — determinística, antes da LLM.
            if await _maybe_consulta_financeira(m, client, texto.lower()):
                return
            if not parser.is_enabled():
                await m.answer("Não entendi. Use /ajuda (ou /rh_teste, /cp_teste)."); return
            parsed = await parser.parse(m.text or "")
            if not parsed:
                await m.answer("Não consegui interpretar agora. Tente de novo ou use /ajuda."); return
            await _tratar_parse(m, store, client, parsed)
        except Exception as e:  # nunca deixar o handler morrer em silêncio
            log_event("freeform_excecao", err=type(e).__name__, level="error")
            await m.answer("⚠️ Tive um erro ao processar sua mensagem. Tente de novo ou use /ajuda.")

    return router


def _idem_for(draft) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    return gerar_idempotency_key(chat_id=draft.chat_id, draft_id=draft.id,
                                 intent=draft.intent or "x", ts_min=ts)


async def _confirmar(m: Message, store, client, settings, d) -> None:
    """Resolve IDs, valida e EXECUTA a escrita (POST). Atualiza status do rascunho."""
    if d.status == "executado":
        await m.answer(f"Pendência {d.id} já foi executada (sem duplicar)."); return
    intent = d.intent or ""
    if intent not in WRITE_TOOLS:
        store.set_status(d.id, "confirmado")
        await m.answer(f"✅ Pendência {d.id} confirmada (sem ação de escrita associada)."); return

    # 1) resolver nomes→IDs + defaults
    try:
        payload, faltando, pergunta = await resolve.resolver(client, d)
    except FinanceAPIError as e:
        await m.answer(friendly(e)); return
    store.update(d.id, payload_extraido={**d.payload_extraido, **payload})
    if pergunta:
        store.update(d.id, campos_faltando=faltando, status="pendente")
        await m.answer(f"{pergunta}\n(corrija com: corrigir {d.id} <campo> <valor>)"); return

    # 2) validar payload pela tool
    tool = WRITE_TOOLS[intent]
    built = tool.build_payload({**d.payload_extraido, **payload})
    miss = validar_payload(tool, built)
    if miss:
        store.update(d.id, campos_faltando=miss, status="pendente")
        await m.answer(f"Faltam dados: {', '.join(miss)} (corrigir {d.id} <campo> <valor>)"); return

    # 3) gating + POST
    if not settings.can_write:
        motivo = "WRITE_ENABLED=false" if not settings.write_enabled else "sem chave de escrita"
        store.set_status(d.id, "confirmado")
        await m.answer(f"✅ Confirmado, mas escrita desabilitada ({motivo}). Rascunho pronto para gravar depois."); return

    idem = d.idempotency_key or _idem_for(d)
    store.update(d.id, idempotency_key=idem, payload_extraido={**d.payload_extraido, **payload})
    d = store.get(d.id)
    d.status = "confirmado"  # exigido pelo gating de executar_write
    res = await executar_write(client, intent=intent, draft=d, idempotency_key=idem)
    if res.ok:
        store.update(d.id, status="executado", resultado_api=res.data)
        await m.answer(f"✅ {res.text}\n{fmt.resultado_write(res.data)}")
    else:
        store.update(d.id, status="erro", erro_api=res.text)
        await m.answer(f"⚠️ Não gravei: {res.text}")


# Frases naturais → ação de pendência (sem número).
_CONFIRM_WORDS = {"confirmar", "confirma", "confirmo", "pode confirmar", "pode lançar",
                  "pode lancar", "pode gravar", "sim", "ok", "isso", "manda"}
_CANCEL_WORDS = {"cancelar", "cancela", "cancelo", "não", "nao", "deixa pra la", "deixa pra lá", "esquece"}
# SOMENTE rascunhos/pendências do PRÓPRIO agente (local SQLite). Contas reais do
# financeiro ("em aberto", "a pagar", "vencidas"...) NÃO entram aqui — são consulta.
_PEND_WORDS = {"pendencias", "pendências", "rascunhos", "meus rascunhos",
               "rascunhos abertos", "rascunhos pendentes",
               "listar pendencias", "listar pendências"}


def _aguardando(store, uid: int) -> list:
    return [d for d in store.list_active(uid)
            if d.status in ("aguardando_confirmacao", "pendente", "confirmado")]


# Verbos/indícios de que a mensagem é um NOVO lançamento (não resposta a uma pergunta).
_VERBOS_NOVO = ("comprei", "paguei", "lança", "lanca", "lancar", "lançar", "adiciona",
                "coloca", "registra", "anota", "fiz ", "soma ", "gastei", "recebi")


def _tem_default(campo: str) -> bool:
    """True se o campo é preenchido automaticamente por default/resolução (não perguntar)."""
    campo = (campo or "").strip()
    if campo in ("formaPagamento",):
        return bool(defaults.get("formaPagamentoPadrao"))
    if campo in ("contaBancariaId", "contaBancaria"):
        return defaults.get("contaBancariaPadraoId") is not None
    if campo in ("categoriaId", "categoria", "categoriaPalavra"):
        return defaults.get("categoriaPadraoId") is not None
    if campo in ("obraId", "obra"):
        return defaults.get("obraPadraoId") is not None
    if campo in ("destino",):
        return bool(defaults.get("rh.destinoPadrao"))
    if campo in ("dataVencimento", "dataPagamento", "data", "qtd", "descricao"):
        return True  # têm fallback (hoje/amanhã, qtd=1, descrição genérica)
    return False


# "comprei ... vence dia X" SEM dizer que pagou = conta A PAGAR (pendente), não paga.
_SINAL_VENCIMENTO = ("vence", "vencimento", "vencer", "a prazo", "fiado",
                     "para o dia", "pro dia", "até dia", "ate dia", "boleto")
_SINAL_PAGO = ("paguei", "quitei", "à vista", "a vista", "saiu da conta", "debitei",
               "já paguei", "ja paguei", "pago em", "foi pago", "paga em", "no pix agora")


def _reclassificar_conta(intent: str, texto: str) -> str:
    """A LLM às vezes marca 'paga' quando o usuário fala de VENCIMENTO sem dizer que
    pagou ('comprei ... vence dia 25/06' = compra a prazo). Regra de negócio do
    usuário: nesse caso é conta a pagar PENDENTE (registra só vencimento, sem 'pago em')."""
    if intent != "criar_conta_pagar_paga":
        return intent
    t = (texto or "").lower()
    tem_venc = any(s in t for s in _SINAL_VENCIMENTO)
    tem_pago = any(s in t for s in _SINAL_PAGO)
    return "criar_conta_pagar" if (tem_venc and not tem_pago) else intent


# Campos que só fazem sentido em conta PAGA (não devem aparecer numa pendente).
_CAMPOS_PAGAMENTO = ("dataPagamento", "formaPagamento", "contaBancariaId",
                     "contaBancariaAlias", "contaBancariaFinal")


def _sanitizar_fields(intent: str, fields: dict | None) -> dict:
    """Remove de uma conta a pagar PENDENTE os campos de pagamento que a LLM possa ter
    devolvido (ex.: dataPagamento alucinado). Sem isso, o valor cru vaza no resumo
    porque o resolve da pendente não processa esses campos."""
    f = dict(fields or {})
    if intent == "criar_conta_pagar":  # pendente
        for k in _CAMPOS_PAGAMENTO:
            f.pop(k, None)
    return f


def _sem_pergunta_final(texto: str) -> str:
    """Remove a última frase interrogativa de uma narração, para não duplicar a
    pergunta canônica do slot-fill (a LLM às vezes já pergunta no próprio 'reply')."""
    t = (texto or "").strip()
    if not t.endswith("?"):
        return t
    corte = max(t.rfind(". "), t.rfind("! "), t.rfind("? ", 0, len(t) - 1))
    return t[:corte + 1].strip() if corte != -1 else ""


def _montar_pergunta(reply: str, pergunta: str, hint: str) -> str:
    """Monta a mensagem de pergunta com a pergunta aparecendo UMA única vez (narração
    da LLM sem a pergunta repetida) + dica de fluxo."""
    partes = [p for p in (_sem_pergunta_final(reply), (pergunta or "").strip()) if p]
    corpo = "\n\n".join(partes)
    return f"{corpo}\n{hint}" if corpo else hint


# ════════════════════════════════════════════════════════════════════════
# Consultas financeiras (contas a pagar REAIS do BRGlobal) — SOMENTE READ.
# Domínio diferente de "pendências" (rascunhos locais). Nunca responde
# "Você não tem pendências" a uma pergunta sobre contas reais.
# ════════════════════════════════════════════════════════════════════════
_TZ_SP = "America/Sao_Paulo"
# Verbos de ESCRITA: se presentes, não é consulta (deixa o parser/reclassificação cuidar).
_VERBOS_ESCRITA = ("comprei", "gastei", "lança", "lanca", "lancar", "lançar", "anota",
                   "anote", "registra", "registre", "coloca", "adiciona", "recebi")


def hoje_sp() -> date:
    """Data local em America/Sao_Paulo (não depende do TZ do servidor/host)."""
    try:
        return datetime.now(ZoneInfo(_TZ_SP)).date()
    except Exception:  # tzdata ausente em algum host → fallback
        return date.today()


def _re_dias(t: str) -> int | None:
    m = re.search(r"pr[oó]xim\w*\s+(\d{1,3})\s+dias?", t)
    return int(m.group(1)) if m else None


def _re_conta_id(t: str) -> int | None:
    m = re.search(r"(?:conta|id|n[ºo]|#)\s*#?\s*(\d{1,7})\b", t)
    return int(m.group(1)) if m else None


def _re_fornecedor(t: str) -> str | None:
    m = re.search(r"\bcontas?\s+d[aeo]\s+([a-zçãõáéíóúâêô0-9][\w .'\-]{1,40})", t) \
        or re.search(r"\bpagar\s+(?:a\s+|o\s+)?(?:conta\s+)?d[aeo]\s+([\w .'\-]{2,40})", t) \
        or re.search(r"\bfornecedor\s+([\w .'\-]{2,40})", t)
    if not m:
        return None
    nome = re.split(r"\b(em aberto|aberta|vencid\w*|hoje|essa|esta|para|pra|por|no|na)\b",
                    m.group(1).strip(" ?.!,"))[0].strip(" ?.!,")
    return nome or None


def _classificar_consulta_financeira(texto: str) -> dict | None:
    """Heurística determinística (0-token): classifica perguntas sobre CONTAS A PAGAR
    REAIS. Retorna {tipo, dias?, fornecedor?, contaId?} ou None (não é consulta)."""
    t = (texto or "").lower().strip()
    if not t or any(v in t for v in _VERBOS_ESCRITA):
        return None

    def has(*subs: str) -> bool:
        return any(s in t for s in subs)

    if has("dados para pagar", "dados de pagamento", "dados pra pagar", "me passa os dados",
           "qual o pix", "qual e o pix", "qual é o pix", "pix da conta", "pix dessa",
           "codigo de barras", "código de barras", "linha digit", "boleto da conta",
           "boleto dessa", "me manda o boleto", "como pago essa", "como pagar essa"):
        return {"tipo": "dados_pagamento", "fornecedor": _re_fornecedor(t), "contaId": _re_conta_id(t)}
    if has("vencida", "vencidas", "atrasada", "atrasadas", "em atraso", "venceu", "vencido"):
        return {"tipo": "vencidas"}
    if has("vence hoje", "vencem hoje", "vencendo hoje", "vencer hoje", "vence hj", "vencem hj"):
        return {"tipo": "hoje"}
    if "semana" in t and has("conta", "venc", "aberto", "pagar", "boleto", "pagamento"):
        return {"tipo": "semana"}
    if has("contas pagas", "conta paga", "que contas paguei", "quais contas paguei",
           "contas que paguei", "historico de pagamento", "histórico de pagamento"):
        return {"tipo": "pagas"}
    nd = _re_dias(t)
    if nd is not None:
        return {"tipo": "proximos", "dias": nd}
    if has("proximos pagamentos", "próximos pagamentos", "proximas contas", "próximas contas",
           "proximos vencimentos", "próximos vencimentos", "a vencer", "proximos dias", "próximos dias"):
        return {"tipo": "proximos"}
    if has("em aberto", "contas abertas", "boletos em aberto", "pagamentos em aberto",
           "o que tenho pra pagar", "o que tenho para pagar", "o que preciso pagar",
           "quais contas preciso pagar", "que contas tenho", "quais contas tenho",
           "tenho contas a pagar", "me mostra as contas", "me mostra os pagamentos",
           "lista de contas", "contas a pagar", "contas pra pagar", "contas para pagar"):
        return {"tipo": "em_aberto"}
    return None


async def _buscar_cp(client, params: dict) -> dict:
    """GET /financeiro/contas-pagar/buscar (read-only) → {itens, total, hasMore}."""
    res = await client.get_v2("financeiro/contas-pagar/buscar", params)
    d = res.get("data") if isinstance(res, dict) else res
    d = d if isinstance(d, dict) else {}
    return {"itens": d.get("candidatos") or [], "total": d.get("total"),
            "hasMore": bool(d.get("hasMore"))}


async def _buscar_cp_paginado(client, base: dict, cap_paginas: int = 6) -> list:
    """Pagina a /buscar (limit 200) até hasMore=false ou o cap (a API não tem range de
    vencimento; janelas são filtradas no cliente)."""
    itens, page = [], 1
    while page <= cap_paginas:
        r = await _buscar_cp(client, {**base, "limit": 200, "page": page})
        itens.extend(r["itens"])
        if not r["hasMore"]:
            break
        page += 1
    return itens


def _venc_date(c: dict):
    s = (c.get("dataVencimento") or "")[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


async def _pendentes_por_vencimento(client, *, de=None, ate=None, antes_de=None) -> list:
    """Pendentes filtradas por janela de vencimento (cliente). `antes_de` → vencidas
    (v < antes_de); `de..ate` → intervalo inclusivo."""
    todas = await _buscar_cp_paginado(client, {"status": "pendente",
                                               "orderBy": "dataVencimento", "order": "asc"})
    sel = []
    for c in todas:
        v = _venc_date(c)
        if v is None:
            continue
        if antes_de is not None and v < antes_de:
            sel.append(c)
        elif de is not None and ate is not None and de <= v <= ate:
            sel.append(c)
    return sel


async def _consulta_dados_pagamento(client, spec: dict) -> str:
    cid, forn = spec.get("contaId"), spec.get("fornecedor")
    if cid:
        for status in ("pendente", "pago"):
            for c in await _buscar_cp_paginado(client, {"status": status,
                                                        "orderBy": "dataVencimento", "order": "asc"}):
                if str(c.get("contaPagarId") or c.get("id")) == str(cid):
                    return fmt.dados_pagamento(c)
        return f"{fmt._CONSULTEI} e não encontrei a conta {cid}."
    if not forn:
        return ("De qual conta? Diga o fornecedor ou o Conta ID — ex.: "
                "'dados para pagar a conta da Ligar'.")
    r = await _buscar_cp(client, {"status": "pendente", "fornecedor": forn,
                                  "orderBy": "dataVencimento", "order": "asc", "limit": 50})
    itens = r["itens"]
    if not itens:
        return f"{fmt._CONSULTEI} e não encontrei conta em aberto da {forn}."
    return fmt.dados_pagamento(itens[0]) if len(itens) == 1 else fmt.escolher_conta(itens, forn)


async def _executar_consulta(client, spec: dict) -> str:
    """Executa a consulta financeira read-only e devolve o texto formatado."""
    tipo = (spec or {}).get("tipo", "em_aberto")
    try:
        if tipo == "dados_pagamento":
            return await _consulta_dados_pagamento(client, spec)
        if tipo == "hoje":
            r = await _buscar_cp(client, {"status": "pendente", "dataVencimento": hoje_sp().isoformat(),
                                          "orderBy": "dataVencimento", "order": "asc", "limit": 50})
            return fmt.consulta_contas(r["itens"], "que vencem hoje", r["total"])
        if tipo == "vencidas":
            itens = await _pendentes_por_vencimento(client, antes_de=hoje_sp())
            return fmt.consulta_contas(itens, "vencidas (em aberto)")
        if tipo == "semana":
            h = hoje_sp(); fim = h + timedelta(days=(6 - h.weekday()))  # hoje até domingo
            itens = await _pendentes_por_vencimento(client, de=h, ate=fim)
            return fmt.consulta_contas(itens, "em aberto para esta semana")
        if tipo == "proximos" and spec.get("dias"):
            n = min(90, max(1, int(spec["dias"]))); h = hoje_sp()
            itens = await _pendentes_por_vencimento(client, de=h, ate=h + timedelta(days=n))
            return fmt.consulta_contas(itens, f"em aberto nos próximos {n} dias")
        if tipo == "pagas":
            r = await _buscar_cp(client, {"status": "pago", "orderBy": "dataPagamento",
                                          "order": "desc", "limit": 10})
            return fmt.consulta_contas(r["itens"], "pagas (mais recentes)", r["total"])
        # em_aberto e proximos sem N → próximas a vencer (pendentes), ordenadas por vencimento
        r = await _buscar_cp(client, {"status": "pendente", "orderBy": "dataVencimento",
                                      "order": "asc", "limit": 10})
        return fmt.consulta_contas(r["itens"], "em aberto (próximas a vencer)", r["total"])
    except FinanceAPIError as e:
        return friendly(e)


async def _maybe_consulta_financeira(m: Message, client, texto: str) -> bool:
    """Roteia perguntas sobre contas a pagar REAIS para a API (read-only). True se tratou."""
    spec = _classificar_consulta_financeira(texto)
    if not spec:
        return False
    log_event("consulta_financeira", tipo=spec.get("tipo"))
    await m.answer(await _executar_consulta(client, spec))
    return True


def _parece_resposta_curta(texto: str) -> bool:
    """True se a mensagem parece RESPOSTA a uma pergunta (curta, sem verbo de novo lançamento).
    Evita que 'comprei 11 cabos...' seja capturado como resposta de um rascunho pendente."""
    low = (texto or "").strip().lower()
    if any(v in low for v in _VERBOS_NOVO):
        return False
    # respostas típicas: 'pagamento', 'vale', 'condor', 'final 97', 'cabos de vassoura', '12'
    return len(low.split()) <= 5


# Campos do rascunho que aceitam resposta de texto livre (slot-filling).
_CAMPO_TEXTO = {"descricao", "nomeFornecedor", "nomeFuncionario", "observacao", "observacoes"}
_CAMPO_NUM = {"valor", "valorUnit", "qtd", "categoriaId", "obraId", "contaBancariaId"}


def _set_aguardando(store, d, campo) -> None:
    """Marca que o rascunho d espera a resposta do campo (slot-filling)."""
    store.update(d.id, status="pendente",
                 payload_extraido={**d.payload_extraido, "_aguardando_campo": campo})


def _draft_aguardando_campo(store, uid: int):
    """Retorna (draft, campo) do rascunho pendente que espera uma resposta; ou (None, None)."""
    for d in store.list_active(uid):
        if d.status == "pendente":
            campo = (d.payload_extraido or {}).get("_aguardando_campo")
            if campo:
                return d, campo
    return None, None


async def _preencher_campo(m: Message, store, client, settings, d, campo: str, valor_txt: str) -> None:
    """Preenche o campo aguardado com a resposta do usuário e re-resolve o rascunho."""
    valor: object = valor_txt.strip()
    novo = {**d.payload_extraido}
    if campo == "fornecedorId":
        # resposta à pergunta de fornecedor: id explícito, "outros", ou novo nome p/ re-buscar
        low = valor_txt.strip().lower()
        if valor_txt.strip().isdigit():
            novo["fornecedorId"] = int(valor_txt.strip())
        elif low in ("outros", "outro", "nenhum", "nenhuma"):
            fid_outros = defaults.get("fornecedorOutrosId")
            if fid_outros:
                novo["fornecedorId"] = fid_outros
                novo["observacoes"] = (f"[AJUSTAR FORNECEDOR: {novo.get('nomeFornecedor','?')}] "
                                       f"{novo.get('observacoes','')}").strip()
            else:
                novo["nomeFornecedor"] = valor_txt.strip()  # sem Outros configurado → re-tenta
        else:
            novo["nomeFornecedor"] = valor_txt.strip()  # tratar como novo nome → re-busca
            novo.pop("fornecedorId", None)
    elif campo in _CAMPO_NUM:
        v = valor.replace("R$", "").replace(".", "").replace(",", ".").strip()
        try:
            valor = float(v) if ("." in v) else int(v)
        except ValueError:
            pass
        novo[campo] = valor
    elif campo == "destino":
        low = valor_txt.lower()
        novo["destino"] = "vale" if "vale" in low else "pagamento" if "pag" in low else valor_txt.strip()
    else:
        novo[campo] = valor
    novo.pop("_aguardando_campo", None)
    store.update(d.id, payload_extraido=novo)
    # re-resolve para ver se ainda falta algo
    d = store.get(d.id)
    try:
        payload, faltando, pergunta = await resolve.resolver(client, d)
        store.update(d.id, payload_extraido={**d.payload_extraido, **payload},
                     campos_faltando=faltando)
    except FinanceAPIError:
        pergunta, faltando = None, []
    if pergunta:
        _set_aguardando(store, d, (faltando or [None])[0])
        await m.answer(f"{pergunta}\n(rascunho #{d.id})"); return
    store.set_status(d.id, "aguardando_confirmacao")
    await m.answer(fmt.resumo_rascunho(store.get(d.id)) +
                   "\n\nResponda CONFIRMAR para gravar ou CANCELAR.")


async def _maybe_pendencia_cmd(m: Message, store, client, settings, texto: str) -> bool:
    # Slot-filling: se há rascunho esperando uma resposta, capturá-la — MAS só se a
    # mensagem parecer uma RESPOSTA curta, não uma nova frase de lançamento.
    if texto not in _CONFIRM_WORDS and texto not in _CANCEL_WORDS and texto not in _PEND_WORDS \
            and not texto.startswith(("confirmar ", "cancelar ", "detalhar ", "corrigir ")):
        d, campo = _draft_aguardando_campo(store, m.from_user.id)
        if d and campo and _parece_resposta_curta(texto):
            await _preencher_campo(m, store, client, settings, d, campo, m.text or "")
            return True

    if texto in _PEND_WORDS:
        store.expire_old()
        await m.answer(fmt.lista_pendencias(store.list_active(m.from_user.id))); return True

    # "detalhar" sozinho: 1 pendência → detalha; várias → pede o número. NUNCA vai p/ LLM.
    if texto in ("detalhar", "detalha"):
        abertos = _aguardando(store, m.from_user.id)
        if not abertos:
            await m.answer("Você não tem pendências."); return True
        if len(abertos) > 1:
            await m.answer("Você tem mais de uma pendência. Qual item deseja detalhar? "
                           "Ex.: detalhar " + str(abertos[-1].id) + "\n\n"
                           + fmt.lista_pendencias(abertos)); return True
        await m.answer(fmt.detalhe_pendencia(abertos[0])); return True

    # "corrigir" sozinho: orienta o formato. NUNCA vai p/ LLM.
    if texto in ("corrigir", "corrige"):
        await m.answer("Para corrigir, use: corrigir N <campo> <valor>  (ex.: corrigir 3 valor 50)")
        return True

    # Confirmação NATURAL (sem número): age no único rascunho em aberto.
    # Palavras de controle exatas ("confirmar"/"confirma"/...) NUNCA vão para a LLM.
    _confirm_exato = texto in ("confirmar", "confirma", "confirmo", "confirmar.")
    if texto in _CONFIRM_WORDS:
        abertos = _aguardando(store, m.from_user.id)
        if not abertos:
            if _confirm_exato:
                await m.answer("Você não tem pendências para confirmar."); return True
            return False  # "sim/ok" sem rascunho → deixa cair no parser (pode ser conversa)
        if len(abertos) > 1:
            await m.answer("Você tem mais de uma pendência. Qual deseja confirmar? Ex.: confirmar "
                           + str(abertos[-1].id) + "\n\n" + fmt.lista_pendencias(abertos)); return True
        await _confirmar(m, store, client, settings, abertos[0]); return True

    # Cancelamento NATURAL (sem número).
    _cancel_exato = texto in ("cancelar", "cancela", "cancelo", "cancelar.")
    if texto in _CANCEL_WORDS:
        abertos = _aguardando(store, m.from_user.id)
        if not abertos:
            if _cancel_exato:
                await m.answer("Você não tem pendências para cancelar."); return True
            return False  # "não/deixa pra lá" sem rascunho → pode ser conversa
        if len(abertos) > 1:
            await m.answer("Você tem mais de uma pendência. Qual deseja cancelar? Ex.: cancelar "
                           + str(abertos[-1].id) + "\n\n" + fmt.lista_pendencias(abertos)); return True
        store.set_status(abertos[0].id, "cancelado")
        await m.answer(f"❌ Pendência {abertos[0].id} cancelada. (nenhum POST executado)"); return True

    # corrigir N campo valor
    if texto.startswith("corrigir "):
        parts = (m.text or "").split(maxsplit=3)
        if len(parts) < 4 or not parts[1].isdigit():
            await m.answer("Uso: corrigir N <campo> <valor>"); return True
        d = store.get(int(parts[1]))
        if not d or d.user_id != m.from_user.id:
            await m.answer("Pendência não encontrada."); return True
        campo, valor = parts[2], parts[3]
        novo = {**d.payload_extraido, campo: valor}
        store.update(d.id, payload_extraido=novo)
        await m.answer(fmt.detalhe_pendencia(store.get(d.id))); return True

    for verbo in ("detalhar", "cancelar", "confirmar"):
        if texto.startswith(verbo + " "):
            resto = texto[len(verbo) + 1:].strip()
            if not resto.isdigit():
                return False
            d = store.get(int(resto))
            if not d or d.user_id != m.from_user.id:
                await m.answer("Pendência não encontrada."); return True
            if verbo == "detalhar":
                await m.answer(fmt.detalhe_pendencia(d))
            elif verbo == "cancelar":
                store.set_status(d.id, "cancelado")
                await m.answer(f"❌ Pendência {d.id} cancelada. (nenhum POST executado)")
            elif verbo == "confirmar":
                await _confirmar(m, store, client, settings, d)
            return True
    return False


async def _tratar_parse(m: Message, store, client, parsed: dict) -> None:
    intent = parsed.get("intent", "indefinido")
    reply = (parsed.get("reply") or "").strip()

    # Conversa / cálculo / consulta → responde sem criar rascunho.
    if intent in ("conversa", "consulta", "pendencias"):
        if intent == "pendencias" and store and store.available:
            store.expire_old()
            await m.answer(fmt.lista_pendencias(store.list_active(m.from_user.id))); return
        if intent == "consulta":
            # Consulta a contas a pagar REAIS (read-only). Usa consultaTipo da LLM; se
            # ausente, cai no classificador determinístico; default em_aberto.
            fields = parsed.get("fields") or {}
            tipo = fields.get("consultaTipo")
            if tipo:
                spec = {"tipo": tipo, "dias": fields.get("dias"),
                        "fornecedor": fields.get("nomeFornecedor"), "contaId": fields.get("contaId")}
            else:
                spec = _classificar_consulta_financeira(m.text or "") or {"tipo": "em_aberto"}
            await m.answer(await _executar_consulta(client, spec)); return
        await m.answer(reply or "Certo!"); return

    # Não é escrita conhecida → conversa/ajuda.
    if intent in ("indefinido", None) or intent not in WRITE_TOOLS:
        await m.answer(reply or parsed.get("question") or "Não entendi. Pode reformular? (ou /ajuda)")
        return

    if not store or not store.available:
        await m.answer("⚠️ Entendi um lançamento, mas rascunhos estão indisponíveis (sem volume)."); return

    # Regra de negócio: "comprei ... vence dia X" (sem dizer que pagou) é conta a pagar
    # PENDENTE, não paga. Reclassifica antes de criar o rascunho.
    intent_ajustado = _reclassificar_conta(intent, m.text or "")
    if intent_ajustado != intent:
        log_event("reclassificou_conta", de=intent, para=intent_ajustado)
        intent = intent_ajustado
        reply = ""  # a narração da LLM assumia 'paga'; evita contradição com o resumo pendente

    dominio = ("rh" if "lancamento" in intent else "financeiro")
    d = store.create(chat_id=m.chat.id, user_id=m.from_user.id, texto=m.text or "",
                     dominio=dominio, intent=intent,
                     payload=_sanitizar_fields(intent, parsed.get("fields")),
                     faltando=parsed.get("missing") or [])
    pre = (reply + "\n\n") if reply else ""   # mostra o que a LLM entendeu/calculou

    # Só perguntar o que a LLM marcou como faltante E que NÃO tem default/resolução automática.
    # (forma, conta, categoria, obra e destino-com-default são preenchidos pelo resolve.)
    falta_real = [c for c in (parsed.get("missing") or []) if not _tem_default(c)]
    if parsed.get("shouldAsk") and parsed.get("question") and falta_real:
        _set_aguardando(store, d, falta_real[0])
        await m.answer(_montar_pergunta(reply, parsed["question"],
                                        f"(rascunho #{d.id} — responda, ou diga 'cancelar')")); return
    # Resolve nomes→IDs + defaults para mostrar um resumo já com o que falta.
    try:
        payload, faltando, pergunta = await resolve.resolver(client, d)
        # campos_faltando vem do resolve (já com defaults aplicados): NÃO manter o
        # 'missing' cru da LLM, senão o resumo mostra "Falta: formaPagamento" mesmo
        # após o Pix padrão ter sido preenchido.
        store.update(d.id, payload_extraido={**d.payload_extraido, **payload},
                     campos_faltando=faltando)
    except FinanceAPIError:
        pergunta, faltando = None, []
    if pergunta:
        _set_aguardando(store, d, (faltando or [None])[0])
        await m.answer(_montar_pergunta(reply, pergunta,
                                        f"(rascunho #{d.id} — depois diga 'confirmar')")); return
    await m.answer(pre + fmt.resumo_rascunho(store.get(d.id)) +
                   "\n\nResponda CONFIRMAR para gravar ou CANCELAR.")
