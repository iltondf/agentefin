"""Command Router — comandos antigos (0 token) + read tools + pendências + escrita.

Fluxo de escrita (sempre): mensagem/comando → RASCUNHO → resumo → `confirmar N`
→ resolve IDs (busca) → valida → POST (Idempotency-Key) → resultado. Gating em tools_write.
A LLM (se ligada) é parser; comandos manuais funcionam mesmo com LLM desligada.
"""
from __future__ import annotations

from datetime import datetime, timezone

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
_PEND_WORDS = {"pendencias", "pendências", "listar pendencias", "listar pendências",
               "o que esta pendente", "o que está pendente", "resumo do dia",
               "mostra o que ficou para confirmar", "o que ficou pendente"}


def _aguardando(store, uid: int) -> list:
    return [d for d in store.list_active(uid)
            if d.status in ("aguardando_confirmacao", "pendente", "confirmado")]


# Verbos/indícios de que a mensagem é um NOVO lançamento (não resposta a uma pergunta).
_VERBOS_NOVO = ("comprei", "paguei", "lança", "lanca", "lancar", "lançar", "adiciona",
                "coloca", "registra", "anota", "fiz ", "soma ", "gastei", "recebi")


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
        store.update(d.id, payload_extraido={**d.payload_extraido, **payload})
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
            await m.answer((reply + "\n\n" if reply else "") +
                           "Para dados, use /resumo, /hoje, /vencidas, /criticas, /painel."); return
        await m.answer(reply or "Certo!"); return

    # Não é escrita conhecida → conversa/ajuda.
    if intent in ("indefinido", None) or intent not in WRITE_TOOLS:
        await m.answer(reply or parsed.get("question") or "Não entendi. Pode reformular? (ou /ajuda)")
        return

    if not store or not store.available:
        await m.answer("⚠️ Entendi um lançamento, mas rascunhos estão indisponíveis (sem volume)."); return

    dominio = ("rh" if "lancamento" in intent else "financeiro")
    d = store.create(chat_id=m.chat.id, user_id=m.from_user.id, texto=m.text or "",
                     dominio=dominio, intent=intent, payload=parsed.get("fields") or {},
                     faltando=parsed.get("missing") or [])
    pre = (reply + "\n\n") if reply else ""   # mostra o que a LLM entendeu/calculou

    # Se a LLM já sabe que falta algo essencial, pergunta direto (e guarda o campo esperado).
    if parsed.get("shouldAsk") and parsed.get("question"):
        campo = (parsed.get("missing") or [None])[0]
        _set_aguardando(store, d, campo)
        await m.answer(f"{pre}{parsed['question']}\n(rascunho #{d.id} — responda, ou diga 'cancelar')"); return
    # Resolve nomes→IDs + defaults para mostrar um resumo já com o que falta.
    try:
        payload, faltando, pergunta = await resolve.resolver(client, d)
        store.update(d.id, payload_extraido={**d.payload_extraido, **payload})
    except FinanceAPIError:
        pergunta, faltando = None, []
    if pergunta:
        _set_aguardando(store, d, (faltando or [None])[0])
        await m.answer(f"{pre}{pergunta}\n(rascunho #{d.id} — depois diga 'confirmar')"); return
    await m.answer(pre + fmt.resumo_rascunho(store.get(d.id)) +
                   "\n\nResponda CONFIRMAR para gravar ou CANCELAR.")
