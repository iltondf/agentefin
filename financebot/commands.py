"""Command Router — handlers determinísticos do Telegram (0 token).

Cada comando: consulta a API (cliente HTTP) → formata → responde. Erros da API
viram mensagem amigável (degradação). Texto livre só usa LLM se habilitada.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from financebot import formatters as fmt
from financebot import llm
from financebot.client import FinanceAPIError, FinanceClient, friendly
from financebot.config import Settings
from financebot.logging_setup import log_event

HELP = (
    "Agente Financeiro BRGlobal 🤖💰\n"
    "Consultas (somente leitura):\n\n"
    "/hoje — contas a pagar que vencem hoje\n"
    "/vencidas — contas vencidas em aberto\n"
    "/criticas — contas críticas (prioridade alta)\n"
    "/proximos7 — a vencer nos próximos 7 dias\n"
    "/painel — painel operacional consolidado\n"
    "/resumo — resumo diário\n"
    "/whoami — diagnóstico da chave do agente\n"
    "/ajuda — esta ajuda"
)


def build_router(client: FinanceClient, settings: Settings) -> Router:
    """Monta o roteador de comandos com o cliente e a config injetados."""
    router = Router()

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
            texto = formatter(data)
        except Exception:
            log_event("fmt_excecao", level="error")
            texto = "⚠️ Não consegui formatar a resposta da API."
        await message.answer(texto)

    @router.message(CommandStart())
    async def _start(m: Message):
        await m.answer(HELP)

    @router.message(Command("ajuda", "help"))
    async def _ajuda(m: Message):
        await m.answer(HELP)

    @router.message(Command("hoje"))
    async def _hoje(m: Message):
        await run_query(m, client.contas_pagar_hoje, fmt.hoje)

    @router.message(Command("vencidas"))
    async def _vencidas(m: Message):
        await run_query(m, client.contas_pagar_vencidas, fmt.vencidas)

    @router.message(Command("criticas"))
    async def _criticas(m: Message):
        await run_query(m, client.contas_pagar_criticas, fmt.criticas)

    @router.message(Command("proximos7"))
    async def _proximos7(m: Message):
        await run_query(m, lambda: client.contas_pagar_proximos(7), fmt.proximos)

    @router.message(Command("painel"))
    async def _painel(m: Message):
        cid = settings.default_conta_bancaria_id
        await run_query(m, lambda: client.painel_operacional(conta_bancaria_id=cid), fmt.painel)

    @router.message(Command("resumo"))
    async def _resumo(m: Message):
        await run_query(m, client.resumo_diario, fmt.resumo)

    @router.message(Command("whoami"))
    async def _whoami(m: Message):
        await run_query(m, client.whoami, fmt.whoami)

    @router.message()
    async def _freeform(m: Message):
        # Texto livre. Sem LLM (padrão): orienta a usar comandos.
        if not llm.is_enabled():
            await m.answer("Não entendi. Use /ajuda para ver os comandos disponíveis.")
            return
        # Com LLM (opcional): usa o resumo diário como contexto e sintetiza.
        try:
            contexto = fmt.resumo(await client.resumo_diario())
        except FinanceAPIError as e:
            await m.answer(friendly(e))
            return
        resposta = await llm.answer_freeform(m.text or "", contexto)
        await m.answer(resposta or "Não consegui responder agora. Use /ajuda.")

    return router
