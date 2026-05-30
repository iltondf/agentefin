# ESTADO ATUAL — handoff entre sessões

> Leia primeiro ao continuar. A documentação é a fonte da verdade. Atualizado em 2026-05-30.

## O que é

`C:\claude sistemas\agente_financeiro` — bot de Telegram **somente leitura** que
consulta o **BRGlobal Financeiro** via `/api/agent/v1`. Stack: Python 3.12+,
aiogram, httpx, pydantic-settings. Repo: `https://github.com/iltondf/agentefin.git`.

## Para recuperar contexto, leia (nesta ordem)

1. `docs/arquitetura/DECISAO_ARQUITETURAL_INICIAL.md`
2. `docs/arquitetura/API_BRGLOBAL.md`
3. `docs/arquitetura/visao-geral.md`
4. `docs/operacao/runbook.md` + `docs/operacao/evidencias-testes.md`
5. `docs/deploy/easypanel.md`
6. `docs/changelog.md` + `docs/checkpoints/`

## Governança (inegociável)

- **Ritual:** implementar → testar → documentar → checkpoint → commit local.
  **Push só com autorização explícita.**
- **Somente leitura.** O agente nunca acessa o banco direto nem escreve no
  financeiro. Fonte da verdade = BRGlobal.
- **Determinístico, 0-token-first.** LLM opcional e **desligada por padrão**.
- Sem framework agêntico / engine / orquestração. Sem Hermes.

## Estado

- **Implementado:** cliente HTTP robusto, command router (`/hoje /vencidas
  /criticas /proximos7 /painel /resumo /whoami /ajuda`), formatters, middleware
  (whitelist + rate limit), LLM opcional, Docker.
- **Testado:** 24 testes (unit + integração over-the-wire) **passando**. Evidência
  real: `/health` 200 e contrato **401** da API de agentes (28-05) — cliente
  degrada corretamente. Ver `docs/operacao/evidencias-testes.md`.
- **Containerizado:** `Dockerfile` + `docker-compose.yml` + `.dockerignore`.
- **Git:** commits locais organizados. **Push NÃO feito** (aguarda autorização).

## Configuração

Ver `.env.example`. Mínimo para rodar: `TELEGRAM_BOT_TOKEN`, `ALLOWED_USER_IDS`,
`BRGLOBAL_API_BASE_URL`, `BRGLOBAL_API_KEY`.

## Pendências / próximos passos

- Gerar a **API Key** real no financeiro (`pnpm agente:create-key`, escopos
  `read:financeiro,read:extrato`) e validar `/whoami` autenticado.
- Deploy no Easypanel (operador): `docs/deploy/easypanel.md`.
- Roadmap (Fase 2+): resumos automáticos (scheduler), contas a receber, write com
  confirmação humana — exige exposição de endpoints no BRGlobal.
