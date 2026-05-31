# Changelog

Formato: data — fase — mudança.

## 2026-05-31 — Planejamento da Fase 2 (LLM como seletor de tools read-only)

- **Planejamento (sem código, sem ativar LLM).** Conceito: LLM apenas interpreta a mensagem
  → escolhe **uma tool permitida** → passa args simples → recebe dados da API → **redige**.
  Nunca acessa banco/Prisma/SQL/HTTP livre, nunca executa/escreve, nunca calcula valor final.
- Comandos atuais viram **tools internas** (`consultar_*`); tools compostas futuras
  (`gerar_resumo_executivo`, `explicar_painel`, `gerar_checklist_prioridades`).
- Docs: `roadmap/PLANO_LLM_FASE_2.md`, `arquitetura/LLM_TOOLS_DESIGN.md`,
  `seguranca/LLM_GUARDRAILS.md`; checkpoint 0006. `LLM_ENABLED=false` (inalterado).

## 2026-05-31 — Deploy real na VPS via Docker Compose e operador interativo documentado

- **Agente EM PRODUÇÃO na VPS** (`root@srv822821`, `~/agentefin`) via Docker Compose
  (commit `9ca3e3e`); container `agentefin` `Up`. Easypanel descartado (limite de 3 projetos).
- Validado ao vivo no Telegram (`brglobalcontas_bot`, token+chave **rotacionados**):
  `/start` e `/painel` com **dados reais** (Vencidas 7 · R$ 19.420,23 · Conciliação 234/75).
- Evidências em `docs/operacao/evidencias-testes.md` §7; checkpoint 0005; manuais de deploy/operador atualizados.
- `LLM_ENABLED=false`, sem scheduler, sem Fase 2, sem novas funcionalidades.

## 2026-05-31 — Operador interativo da VPS (assistente de configuração)

- Novo `scripts/ops/agentefin-vps.sh`: menu (verificar ambiente, **configurar `.env`
  por assistente**, deploy/update, status, logs, restart, parar, validar `/whoami`, checklist).
- Opção 2 troca token/chave/LLM **sem editor**: backup `.env.bak.*`, segredos ocultos e
  mascarados, `chmod 600`, validações. `bash -n` OK. LLM segue **futura** (bot inalterado).
- Doc `docs/deploy/OPERADOR_VPS_INTERATIVO.md` + checkpoint 0004. Sem scheduler, sem Fase 2.

## 2026-05-31 — Preparação de deploy direto na VPS (Docker Compose)

- **Easypanel descartado** (licença gratuita limita a 3 projetos) → deploy via
  **Docker Compose direto na VPS**. Bot por polling: sem porta/domínio/proxy/SSL.
- `docker-compose.yml` ajustado (serviço `agentefin`, sem ports, sem volumes, stateless,
  rotação de logs json-file 10MB×3). Novo guia `docs/deploy/DEPLOY_DIRETO_VPS_DOCKER.md`.
- Scripts `scripts/deploy/vps-docker-{deploy,status,stop}.sh`; `.gitattributes` (LF em `*.sh`).
- `docs/deploy/easypanel.md` marcado como descontinuado. Sem scheduler, sem Fase 2, sem novas funcionalidades.

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
