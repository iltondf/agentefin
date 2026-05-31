# Changelog

Formato: data — fase — mudança.

## 2026-05-31 — Homologação real contra PRODUÇÃO (local)

- API Key do agente criada (id 7, `bgf_live_ecffe92489e…`, escopos `read:financeiro,read:extrato`)
  e **validada**: `/whoami` → **200** contra `https://lixo.brglobal.com.br/api/agent/v1`.
- Comandos testados com **dados reais** (batem com o cron das 05:00): `/vencidas` 7 contas
  R$ 19.420,23; `/resumo`; `/painel` (matches 234/75, sugestões 19); `/hoje`,`/criticas`,`/proximos7` vazios; `/ajuda`.
- Bot `Brglobal_financeiro_bot` em polling **localmente** (não em produção); TLS ok (AVG desligado).
- Pendência: **deploy Easypanel**. ⚠️ **Rotacionar** `TELEGRAM_BOT_TOKEN` e `BRGLOBAL_API_KEY` (expostos no chat).
- Sem push, sem deploy, sem scheduler, sem novas funcionalidades.

## 2026-05-30 — Auditoria final (correções de bugs)

- **Boot com `.env.example` as-is:** `DEFAULT_CONTA_BANCARIA_ID` vazio agora vira
  `None` (field_validator) — antes lançava `ValidationError` no import.
- **Cliente HTTP:** `404` não é mais retentado (retry só em 5xx/rede/timeout/rate-limit).
- **`AccessMiddleware`:** fallback `event.from_user` (robustez).
- +2 testes de regressão → **26 testes**. `docker build` + `docker run` (safe boot) validados.

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
