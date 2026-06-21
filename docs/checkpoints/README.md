# Checkpoints

Índice de marcos. Um checkpoint por fase/auditoria/decisão relevante.

| # | Arquivo | Marco |
|---|---|---|
| 0001 | `CHECKPOINT_IMPLEMENTACAO_INICIAL.md` | MVP leitura implementado, testado, dockerizado, documentado |
| 0002 | `CHECKPOINT_HOMOLOGACAO_PRODUCAO_LOCAL.md` | Homologação real contra produção (dados reais), bot local |
| 0003 | `CHECKPOINT_PREPARACAO_DEPLOY_DIRETO_VPS.md` | Deploy direto na VPS (Docker Compose); Easypanel descartado |
| 0004 | `CHECKPOINT_OPERADOR_VPS_INTERATIVO.md` | Operador interativo (assistente de `.env` + operação) |
| 0005 | `CHECKPOINT_DEPLOY_VPS_DOCKER_REALIZADO.md` | Deploy real na VPS (Docker Compose) — EM PRODUÇÃO |
| 0006 | `CHECKPOINT_PLANEJAMENTO_LLM_TOOLS.md` | Planejamento Fase 2: LLM como seletor de tools read-only |
| 0007 | `CHECKPOINT_PLANEJAMENTO_SECRETARIA_OPERACIONAL.md` | Planejamento: secretária operacional (inbox + rascunhos) |
| 0008 | `CHECKPOINT_PLANEJAMENTO_AGENT_READY_WRITE.md` | Planejamento agent-ready: write tools + rascunhos + confirmação (consolida 0006/0007 com API real) |
| 0009 | `CHECKPOINT_IMPLEMENTACAO_AGENT_READY_TOOLS.md` | Implementação agent-ready: cliente 2-envelopes, registry, rascunhos SQLite, parser, write tools (gated). 51 testes |
| 0010 | `CHECKPOINT_TELEGRAM_FLUXO_E_ESCRITA_REAL.md` | Fluxo Telegram ligado (confirmar→POST) + validação real (#291/#929/#930), idempotência. 57 testes |
| 0011 | `CHECKPOINT_LLM_LINGUAGEM_NATURAL.md` | LLM como fluxo principal: parser robusto, confirmação natural, defaults. 64 testes |
