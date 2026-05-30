# Changelog

Formato: data — fase — mudança.

## 2026-05-30 — Implementação inicial (MVP leitura)

- **ETAPA 0** Auditoria dos projetos de referência; resolvido o erro
  `@prisma/client did not initialize` (gerar via `pnpm run db:generate`);
  descoberta da discrepância de versão (`/api/agent/v1` só existe na base 28-05);
  decisão "não usar Hermes" materializada (bot Telegram limpo sobre `/api/agent/v1`).
  Doc: `docs/arquitetura/DECISAO_ARQUITETURAL_INICIAL.md`.
- **ETAPA 1** Estrutura documental `docs/` criada.
- **ETAPA 2** Mapa da API: `docs/arquitetura/API_BRGLOBAL.md` (endpoints +
  tabela comando→endpoint).
- **ETAPA 3/4** Implementado: `config`, `logging_setup`, `client` (HTTP robusto:
  timeout/retry/erros tipados/degradação), `formatters`, `commands` (router),
  `bot` (middleware whitelist + rate limit), `llm` (opcional, off), `main`.
  Comandos: `/hoje /vencidas /criticas /proximos7 /painel /resumo /whoami /ajuda`.
- **ETAPA 5** 24 testes (unit + integração over-the-wire) passando. Evidência real
  contra a API: `/health` 200 e contrato 401. `docs/operacao/evidencias-testes.md`.
- **ETAPA 6** Docker: `Dockerfile` (`python:3.12-slim` + tzdata, sem porta),
  `docker-compose.yml`, `.dockerignore`, `.env.example`.
- **ETAPA 7** Checkpoint inicial e `ESTADO-ATUAL`.
- **ETAPA 9** Commits locais organizados (sem push).
