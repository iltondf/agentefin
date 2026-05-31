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
5. `docs/deploy/easypanel.md`
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
  id 7). `/vencidas` = 7 contas, R$ 19.420,23 (bate com o cron das 05:00). Ver
  `docs/checkpoints/CHECKPOINT_HOMOLOGACAO_PRODUCAO_LOCAL.md` e `docs/operacao/evidencias-testes.md`.
- **Bot rodando LOCALMENTE** (`python -m main` nesta máquina) — **não em produção**.
- **Containerizado:** `Dockerfile` + `docker-compose.yml` + `.dockerignore`.
- **Git:** commits locais organizados. **Push NÃO feito** (aguarda autorização).

## Configuração

Ver `.env.example`. Mínimo para rodar: `TELEGRAM_BOT_TOKEN`, `ALLOWED_USER_IDS`,
`BRGLOBAL_API_BASE_URL`, `BRGLOBAL_API_KEY`. Em homologação, a config real fica em
`.env` / `.env.homologacao.local` (ambos **gitignored**).

## Pendências / próximos passos

- ✅ API Key gerada e validada (id 7, `bgf_live_`) — homologação real OK.
- **Deploy no Easypanel** (operador): `docs/deploy/easypanel.md`. O bot ainda roda só localmente.
- ⚠️ **Segurança:** **rotacionar** `TELEGRAM_BOT_TOKEN` e `BRGLOBAL_API_KEY` (apareceram em texto no chat de desenvolvimento).
- Roadmap (Fase 2+): resumos automáticos (scheduler — **não ativar sem decisão**),
  contas a receber, write com confirmação humana — exige exposição de endpoints no BRGlobal.
