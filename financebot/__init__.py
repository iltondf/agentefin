"""Agente Financeiro — Telegram bot read-only sobre a API do BRGlobal Financeiro.

Arquitetura (simples e explícita):
    Telegram → Command Router → Finance API Client → BRGlobal API → Resposta

Princípios: determinístico, 0-token-first, somente leitura. LLM é opcional e
desligada por padrão. Sem framework agêntico, sem orquestração, sem engine.
"""

__version__ = "1.0.0"
