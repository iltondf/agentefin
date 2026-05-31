# ESTADO ATUAL — handoff entre sessões

> Leia primeiro ao continuar. A documentação é a fonte da verdade. Atualizado em 2026-05-31.

## O que é

`C:\claude sistemas\agente_financeiro` — bot de Telegram **somente leitura** que
consulta o **BRGlobal Financeiro** via `/api/agent/v1`. Stack: Python 3.12+,
aiogram, httpx, pydantic-settings. Repo: `https://github.com/iltondf/agentefin.git`.

## Para recuperar contexto, leia (nesta ordem)

1. `docs/arquitetura/DECISAO_ARQUITETURAL_INICIAL.md`
2. `docs/arquitetura/API_BRGLOBAL.md`
3. `docs/arquitetura/visao-geral.md`
4. `docs/operacao/runbook.md` + `docs/operacao/evidencias-testes.md`
5. `docs/deploy/DEPLOY_DIRETO_VPS_DOCKER.md`  *(Easypanel descartado)*
6. `docs/changelog.md` + `docs/checkpoints/`

## Governança (inegociável)

- **Ritual:** implementar → testar → documentar → checkpoint → commit local.
  **Push só com autorização explícita.**
- **Somente leitura.** O agente nunca acessa o banco direto nem escreve no
  financeiro. Fonte da verdade = BRGlobal.
- **Determinístico, 0-token-first.** LLM opcional e **desligada por padrão**.
- Sem framework agêntico / engine / orquestração. Sem Hermes. Scheduler **não ativado**.

## Estado

- **Implementado:** cliente HTTP robusto, command router (`/hoje /vencidas
  /criticas /proximos7 /painel /resumo /whoami /ajuda`), formatters, middleware
  (whitelist + rate limit), LLM opcional, Docker.
- **Testado:** 26 testes (unit + integração over-the-wire) **passando**.
- **Homologado em PRODUÇÃO (2026-05-31):** `/whoami` → **200** e **dados reais** nos
  comandos contra `https://lixo.brglobal.com.br/api/agent/v1` (chave `bgf_live_ecffe92489e…`,
  id 7). `/vencidas` = 7 contas, R$ 19.420,23. Ver `docs/checkpoints/` e `docs/operacao/evidencias-testes.md`.
- **Bot local PARADO** (0 instâncias). **Deploy planejado: Docker Compose direto na VPS**
  (Easypanel descartado por limite de 3 projetos) — ver `docs/deploy/DEPLOY_DIRETO_VPS_DOCKER.md`.
- **Git:** `origin/main` atualizado (push feito). Working tree limpo.

## Configuração

Ver `.env.example`. Mínimo: `TELEGRAM_BOT_TOKEN`, `ALLOWED_USER_IDS`,
`BRGLOBAL_API_BASE_URL`, `BRGLOBAL_API_KEY`, `TZ`, `LLM_ENABLED`. A config real fica
em `.env` (na VPS) — **gitignored**, nunca versionar.

## Pendências / próximos passos

- **Deploy direto na VPS (Docker Compose)** — `docs/deploy/DEPLOY_DIRETO_VPS_DOCKER.md`.
  Etapas: (1) rotacionar `TELEGRAM_BOT_TOKEN` + gerar nova `BRGLOBAL_API_KEY`;
  (2) criar `.env` na VPS; (3) `scripts/deploy/vps-docker-deploy.sh`; (4) testar 8 comandos;
  (5) revogar chave antiga id 7 (`agente:revoke-key 7`).
- ⚠️ **Segurança:** token e chave atuais apareceram no chat → usar **novos** no deploy.
- Roadmap (Fase 2+): resumos automáticos (scheduler — **não ativar sem decisão**),
  contas a receber, write com confirmação humana — exige endpoints no BRGlobal.
