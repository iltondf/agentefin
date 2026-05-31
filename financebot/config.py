"""Configuração via variáveis de ambiente (pydantic-settings).

Fonte única de configuração. No container as variáveis vêm do Easypanel;
`.env` é só para desenvolvimento local. Nenhum segredo no código.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Telegram ──
    telegram_bot_token: str = ""
    allowed_user_ids: str = ""  # CSV de IDs numéricos; vazio = nega todos
    rate_limit_per_min: int = 20

    # ── API BRGlobal (fonte da verdade) ──
    brglobal_api_base_url: str = "http://localhost:3333/api/agent/v1"
    brglobal_api_key: str = ""
    http_timeout: float = 30.0
    http_retries: int = 2
    default_conta_bancaria_id: int | None = None

    # ── LLM (opcional — desligada por padrão) ──
    llm_enabled: bool = False
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout: float = 20.0

    # ── Observabilidade ──
    log_level: str = "INFO"
    log_path: str = "logs/app.log"
    tz: str = "America/Sao_Paulo"

    @field_validator("default_conta_bancaria_id", mode="before")
    @classmethod
    def _empty_to_none(cls, v):
        """Trata string vazia (ex.: `.env.example` copiado as-is) como None,
        evitando ValidationError no boot para o campo opcional int."""
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return v

    @property
    def allowed_ids(self) -> set[int]:
        """Conjunto de IDs autorizados (parse do CSV). Vazio = nega todos."""
        out: set[int] = set()
        for part in self.allowed_user_ids.split(","):
            part = part.strip()
            if part.isdigit():
                out.add(int(part))
        return out

    @property
    def log_full_path(self) -> Path:
        p = Path(self.log_path)
        return p if p.is_absolute() else PROJECT_ROOT / p


settings = Settings()
