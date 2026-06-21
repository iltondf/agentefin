"""Configuração via variáveis de ambiente (pydantic-settings).

Fonte única de configuração. No container as variáveis vêm do operador/VPS;
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
    brglobal_api_base_url: str = "https://lixo.brglobal.com.br/api/agent/v1"
    # Compatibilidade: chave read antiga. GET usa read_api_key se existir, senão esta.
    brglobal_api_key: str = ""
    brglobal_read_api_key: str = ""   # chave de leitura (opcional)
    brglobal_write_api_key: str = ""  # chave de escrita (obrigatória p/ POST)
    http_timeout: float = 32.0
    http_retries: int = 2
    default_conta_bancaria_id: int | None = None

    # ── Escrita (gating) ──
    write_enabled: bool = False  # POST só ocorre se True E houver write key

    # ── Rascunhos / dados ──
    drafts_enabled: bool = True
    data_dir: str = "data"          # no container: /app/data (volume)
    defaults_file: str = "defaults.yaml"

    # ── LLM (opcional — desligada por padrão) ──
    llm_enabled: bool = False
    llm_provider: str = "openrouter"
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    openrouter_api_key: str = ""  # alias preferido quando provider=openrouter
    llm_model: str = ""
    llm_timeout: float = 20.0

    # ── Observabilidade ──
    log_level: str = "INFO"
    log_path: str = "logs/app.log"
    tz: str = "America/Sao_Paulo"

    @field_validator("default_conta_bancaria_id", mode="before")
    @classmethod
    def _empty_to_none(cls, v):
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
    def read_key(self) -> str:
        """Chave para GET: read_api_key se definida, senão a compatível antiga."""
        return self.brglobal_read_api_key or self.brglobal_api_key

    @property
    def write_key(self) -> str:
        """Chave para POST (nunca usa a read). Vazia => escrita indisponível."""
        return self.brglobal_write_api_key

    @property
    def llm_effective_key(self) -> str:
        """Chave LLM: openrouter_api_key tem precedência quando provider=openrouter."""
        if self.llm_provider == "openrouter" and self.openrouter_api_key:
            return self.openrouter_api_key
        return self.llm_api_key or self.openrouter_api_key

    @property
    def can_write(self) -> bool:
        """True só se escrita habilitada E chave de escrita presente."""
        return self.write_enabled and bool(self.write_key)

    @property
    def data_path(self) -> Path:
        p = Path(self.data_dir)
        return p if p.is_absolute() else PROJECT_ROOT / p

    @property
    def defaults_path(self) -> Path:
        p = Path(self.defaults_file)
        return p if p.is_absolute() else PROJECT_ROOT / p

    @property
    def log_full_path(self) -> Path:
        p = Path(self.log_path)
        return p if p.is_absolute() else PROJECT_ROOT / p


settings = Settings()
