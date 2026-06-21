# Checkpoint 0009 — Implementação Agent-Ready (tools + rascunhos + parser)

**Data:** 2026-06-21. **Tipo:** implementação (sem POST real; WRITE/LLM off por padrão).

## Implementado
- **Cliente HTTP 2-envelopes** (`client.py`): `get_legacy`/`get_v2`/`post_v2`; erros v2
  (errorCode/candidatos/camposFaltando); chaves read/write separadas; retry seguro; idempotência.
- **Config** (`config.py`): `BRGLOBAL_READ_API_KEY`, `BRGLOBAL_WRITE_API_KEY` (+ compat
  `BRGLOBAL_API_KEY`), `WRITE_ENABLED`, `DRAFTS_ENABLED`, `DATA_DIR`, `DEFAULTS_FILE`,
  `LLM_PROVIDER/MODEL`, `OPENROUTER_API_KEY`. Props `read_key/write_key/can_write/llm_effective_key`.
- **Registry de tools** (`tools.py`): 21 read tools (antigas legacy + novas v2).
- **Write tools** (`tools_write.py`): 6 tools com `build_payload`/`validar_payload`/idempotency +
  **tripla trava** (WRITE_ENABLED+chave, confirmação, payload válido). `fechamento→CP` não incluído (501).
- **Rascunhos SQLite** (`drafts.py`): `fin_draft` em `DATA_DIR`; comandos `/pendencias`,
  `detalhar/confirmar/cancelar N`. Volume `/app/data` no compose.
- **Defaults** (`defaults.py` + `defaults.yaml`): obra/conta/forma/categoria/diária; mostrados no resumo.
- **LLM parser** (`parser.py`): JSON estruturado, off por padrão, fallback, sem segredo, sem POST.
- **Comandos** (`commands.py`): antigos preservados (0 token) + buscas debug + pendências + freeform.
- **Operador VPS** (`agentefin-vps.sh`): novas envs, validar API leitura (8) e **escrita /whoami sem POST (9)**.
- **Docker**: volume `/app/data`; `COPY defaults.yaml`; `DATA_DIR=/app/data`.

## Testes
**51 passed** (unwrap legacy+v2, registry, drafts, write gating, idempotência, defaults, parser,
regressão dos comandos antigos). `bash -n` OK nos 4 scripts. Sem segredo rastreado.

## Estado final desta rodada
- `WRITE_ENABLED=false`, `LLM_ENABLED=false` (padrão). **POST real não executado.**
- Comandos antigos **intactos**. Deploy/VPS: ver próximo passo (não alterado nesta rodada salvo push).

## Pendências
- Testes READ em produção (exigem `.env` com chave) — registrar em EVIDENCIAS.
- Testes WRITE reais: só após backup confirmado + chave write + `/whoami` write +
  frase `AUTORIZO_POST_REAL_AGENT_READY`.
- Fluxo conversacional de escrita: rascunho criado pelo parser; a execução real (POST a partir
  do "confirmar N") liga rascunho→tools_write — fase a amadurecer com a chave write disponível.

## Docs
`roadmap/PLANO_AGENT_READY_FASE_WRITE.md` (plano), `arquitetura/*_IMPLEMENTADO.md`,
`seguranca/WRITE_RUNTIME_GUARDRAILS.md` + `LLM_PARSER_GUARDRAILS.md`,
`operacao/COMO_USAR_*` + `EVIDENCIAS_AGENT_READY_WRITE_TESTS.md`.
