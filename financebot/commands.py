"""Command Router — comandos antigos (0 token, intactos) + read tools novas + pendências.

A LLM (se habilitada) é parser/seletor: monta rascunho; NUNCA executa POST.
Escrita só ocorre via confirmação explícita do usuário (e gating em tools_write).
"""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from financebot import formatters as fmt
from financebot import parser
from financebot.client import FinanceAPIError, FinanceClient, friendly
from financebot.config import Settings
from financebot.logging_setup import log_event
from financebot.tools import build_read_registry

HELP = (
    "Agente Financeiro BRGlobal 🤖💰\n"
    "Consultas (somente leitura):\n"
    "/hoje /vencidas /criticas /proximos7 /painel /resumo /whoami\n\n"
    "Buscas (debug):\n"
    "/buscar_funcionario <nome> · /buscar_fornecedor <nome> · /buscar_conta <nome>\n\n"
    "Pendências (rascunhos):\n"
    "/pendencias · detalhar N · confirmar N · cancelar N\n\n"
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
            await message.answer(friendly(e))
            return
        except Exception:
            log_event("cmd_excecao", level="error")
            await message.answer("⚠️ Erro inesperado ao consultar a API financeira.")
            return
        try:
            await message.answer(formatter(data))
        except Exception:
            log_event("fmt_excecao", level="error")
            await message.answer("⚠️ Não consegui formatar a resposta da API.")

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

    # ── Buscas (debug): mostram candidatos crus resumidos ──
    async def _busca(m: Message, tool_name: str, arg_key: str):
        termo = (m.text or "").split(maxsplit=1)
        if len(termo) < 2:
            await m.answer("Uso: informe um nome. Ex.: /buscar_fornecedor Areião")
            return
        tool = read_tools[tool_name]
        try:
            res = await tool.run({arg_key: termo[1].strip()})
        except FinanceAPIError as e:
            await m.answer(friendly(e)); return
        except Exception:
            await m.answer("⚠️ Erro na busca."); return
        await m.answer(fmt.candidatos_v2(res.data))

    @router.message(Command("buscar_funcionario"))
    async def _bf(m: Message): await _busca(m, "buscar_funcionarios", "nome")

    @router.message(Command("buscar_fornecedor"))
    async def _bfor(m: Message): await _busca(m, "buscar_fornecedores", "nome")

    @router.message(Command("buscar_conta"))
    async def _bc(m: Message): await _busca(m, "buscar_contas_bancarias", "nome")

    # ── Pendências / rascunhos ──
    @router.message(Command("pendencias"))
    async def _pend(m: Message):
        if not store or not store.available:
            await m.answer("⚠️ Rascunhos indisponíveis (sem persistência). Configure DATA_DIR/volume.")
            return
        store.expire_old()
        await m.answer(fmt.lista_pendencias(store.list_active(m.from_user.id)))

    # ── Texto livre ──
    @router.message()
    async def _freeform(m: Message):
        texto = (m.text or "").strip().lower()
        # comandos-mensagem de pendências (sem barra)
        if store and store.available:
            tratado = await _maybe_pendencia_cmd(m, store, texto)
            if tratado:
                return
        if not parser.is_enabled():
            await m.answer("Não entendi. Use /ajuda para ver os comandos disponíveis.")
            return
        # LLM parser → rascunho (NUNCA executa POST)
        parsed = await parser.parse(m.text or "")
        if not parsed:
            await m.answer("Não consegui interpretar agora. Use /ajuda.")
            return
        await _tratar_parse(m, store, parsed)

    return router


async def _maybe_pendencia_cmd(m: Message, store, texto: str) -> bool:
    """Trata 'pendências/detalhar N/confirmar N/cancelar N' como mensagem. Retorna True se tratou."""
    if texto in ("pendencias", "pendências", "listar pendencias", "listar pendências"):
        store.expire_old()
        await m.answer(fmt.lista_pendencias(store.list_active(m.from_user.id)))
        return True
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
                await m.answer(f"❌ Pendência {d.id} cancelada.")
            elif verbo == "confirmar":
                # Confirmação humana: marca confirmado. A EXECUÇÃO real (POST) é gated por
                # WRITE_ENABLED + chave de escrita (tools_write.executar_write).
                store.set_status(d.id, "confirmado")
                await m.answer(
                    f"✅ Pendência {d.id} confirmada.\n"
                    "ℹ️ Execução de escrita ocorre apenas com WRITE_ENABLED=true e chave de escrita."
                )
            return True
    return False


async def _tratar_parse(m: Message, store, parsed: dict) -> None:
    """Mostra resumo do que a LLM entendeu e guarda rascunho (não grava)."""
    intent = parsed.get("intent", "indefinido")
    if intent.startswith("consultar_"):
        await m.answer("Entendi uma consulta. Use o comando correspondente (ex.: /resumo).")
        return
    if intent in ("indefinido", None):
        q = parsed.get("question")
        await m.answer(q or "Não entendi o suficiente. Pode reformular?")
        return
    if not store or not store.available:
        await m.answer("⚠️ Entendi um lançamento, mas rascunhos estão indisponíveis (sem persistência).")
        return
    dominio = ("rh" if "rh" in intent or "lancamento" in intent else
               "terceirizado" if "terceiriz" in intent else "financeiro")
    d = store.create(
        chat_id=m.chat.id, user_id=m.from_user.id, texto=m.text or "",
        dominio=dominio, intent=intent, payload=parsed.get("fields") or {},
        faltando=parsed.get("missing") or [],
    )
    if parsed.get("shouldAsk") and parsed.get("question"):
        await m.answer(f"{parsed['question']}\n\n(rascunho #{d.id} salvo — veja em /pendencias)")
    else:
        await m.answer(fmt.detalhe_pendencia(d) + "\n\nResponda: confirmar " + str(d.id) + " | cancelar " + str(d.id))
