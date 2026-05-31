"""Wiring do bot Telegram (aiogram): middleware de acesso + roteador + polling.

Processo único: `python -m main`. Sem porta de entrada (só conexões de saída).
Safe boot: sem token, loga e encerra limpo.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.types import Message, TelegramObject

from financebot.client import FinanceClient
from financebot.commands import build_router
from financebot.config import settings
from financebot.logging_setup import log_event, setup_logging


class AccessMiddleware(BaseMiddleware):
    """Whitelist rígida + rate limit por usuário (janela deslizante de 60s)."""

    def __init__(self) -> None:
        self._hits: dict[int, deque] = defaultdict(deque)

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user") or getattr(event, "from_user", None)
        uid = user.id if user else None
        if uid is None or uid not in settings.allowed_ids:
            log_event("acesso_negado", uid=uid, level="warning")
            return  # silêncio total para não autorizados

        dq = self._hits[uid]
        now = time.monotonic()
        while dq and now - dq[0] > 60:
            dq.popleft()
        if len(dq) >= settings.rate_limit_per_min:
            log_event("rate_limit", uid=uid, level="warning")
            if isinstance(event, Message):
                await event.answer("⏳ Muitas mensagens em pouco tempo. Aguarde um instante.")
            return
        dq.append(now)
        return await handler(event, data)


def build_client() -> FinanceClient:
    return FinanceClient(
        base_url=settings.brglobal_api_base_url,
        api_key=settings.brglobal_api_key,
        timeout=settings.http_timeout,
        retries=settings.http_retries,
    )


async def run() -> None:
    setup_logging()

    if not settings.telegram_bot_token:
        log_event("telegram_nao_configurado", level="warning")
        print("TELEGRAM_BOT_TOKEN ausente — encerrando (safe boot).")
        return
    if not settings.allowed_ids:
        log_event("whitelist_vazia", level="warning")
    if not settings.brglobal_api_key:
        log_event("api_key_ausente", level="warning")

    client = build_client()
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.message.outer_middleware(AccessMiddleware())
    dp.include_router(build_router(client, settings))

    log_event(
        "bot_start",
        base_url=settings.brglobal_api_base_url,
        llm=settings.llm_enabled,
        allowed=len(settings.allowed_ids),
    )
    await dp.start_polling(bot)
