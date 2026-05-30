# Visão Geral da Arquitetura

```
┌──────────┐   mensagem    ┌──────────────────┐   chamada     ┌──────────────┐
│ Telegram │ ────────────▶ │  Command Router  │ ────────────▶ │ Finance API  │
│  (aiogram│ ◀──────────── │ (financebot.     │ ◀──────────── │   Client     │
│   bot)   │   resposta     │  commands)       │   ToolResult  │ (httpx)      │
└──────────┘                └──────────────────┘                └──────┬───────┘
      ▲                            │ formatação 0-token (Python puro)   │ GET (Bearer)
      │ whitelist + rate limit     ▼                                    ▼
┌──────────┐                ┌──────────────────┐                ┌──────────────┐
│ Access   │                │   formatters     │                │  BRGlobal    │
│Middleware│                │ (texto Telegram) │                │ /api/agent/v1│
└──────────┘                └──────────────────┘                └──────────────┘
```

## Módulos (`financebot/`)

| Arquivo | Responsabilidade |
|---|---|
| `config.py` | Configuração via env (pydantic-settings). Fonte única. |
| `logging_setup.py` | Logs estruturados `chave=valor` (stdout + arquivo rotacionado). |
| `client.py` | **Finance API Client** — GET na API de agentes; timeout, retry, erros tipados, degradação. |
| `formatters.py` | Payload da API → texto Telegram (determinístico, 0 token). |
| `commands.py` | **Command Router** — handlers `/hoje`, `/vencidas`, ... |
| `bot.py` | Wiring aiogram + `AccessMiddleware` (whitelist + rate limit) + polling. |
| `llm.py` | Síntese **opcional** (desligada por padrão). |
| `main.py` (raiz) | Entrypoint: `python -m main`. |

## Princípios aplicados (na ordem)

1. **Simplicidade** — pacote único, sem framework/engine/registry/plugins.
2. **Manutenção** — domínio fino; a regra financeira vive no servidor.
3. **Confiabilidade** — somente leitura; degradação em toda falha; texto puro.
4. **Observabilidade** — logs `chave=valor` por chamada (status, ms, tentativa).
5. **Performance** — 0-token-first; uma chamada HTTP por comando.
6. **Escalabilidade** — processo único, stateless; escala por réplicas se preciso.
