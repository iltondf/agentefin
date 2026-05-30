"""Logging estruturado (chave=valor) → stdout + arquivo rotacionado.

Observabilidade leve (sem stack pesada). REGRA: nunca logar segredos
(token, API key) nem conteúdo financeiro sensível.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from financebot.config import settings

_LOGGER_NAME = "financebot"
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 3
_configured = False


def setup_logging() -> None:
    """Idempotente: configura stdout + arquivo rotacionado uma única vez."""
    global _configured
    if _configured:
        return

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(settings.log_level.upper())
    fmt = logging.Formatter("%(asctime)s %(levelname)-5s %(message)s", "%Y-%m-%d %H:%M:%S")

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    try:
        path = settings.log_full_path
        path.parent.mkdir(parents=True, exist_ok=True)
        fileh = RotatingFileHandler(
            path, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
        )
        fileh.setFormatter(fmt)
        logger.addHandler(fileh)
    except OSError:
        pass  # arquivo é secundário; stdout basta (ex.: container read-only)

    logger.propagate = False
    _configured = True


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)


def _fmt_fields(fields: dict) -> str:
    return " ".join(f"{k}={str(v).replace(' ', '_')}" for k, v in fields.items())


def log_event(event: str, *, level: str = "info", **fields) -> None:
    """Loga um evento como `evento k=v k=v`."""
    logger = get_logger()
    msg = event if not fields else f"{event} {_fmt_fields(fields)}"
    getattr(logger, level, logger.info)(msg)
