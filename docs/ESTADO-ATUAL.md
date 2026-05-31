# ESTADO ATUAL — handoff entre sessões

> Leia primeiro ao continuar. A documentação é a fonte da verdade. Atualizado em 2026-05-31.

## Status: 🟢 EM PRODUÇÃO NA VPS

- **Deploy:** Docker Compose **direto na VPS** (`root@srv822821`, `~/agentefin`), commit `9ca3e3e`.
- **Easypanel:** **descartado** para este agente (licença gratuita limita a 3 projetos).
- **Container VPS:** `agentefin` **ativo** (`python -m main`, sem portas).
- **Bot local:** **parado** (0 instâncias).
- **LLM:** **desativada** (`LLM_ENABLED=false`).
- **Scheduler:** **inexistente**.
- **Fase atual:** **MVP leitura** por comandos Telegram.
- **Próxima fase:** somente **após validação operacional** e decisão explícita.

## O que é

`C:\claude sistemas\agente_financeiro` — bot de Telegram **somente leitura** que
consulta o **BRGlobal Financeiro** via `/api/agent/v1`. Stack: Python 3.12+,
aiogram, httpx, pydantic-settings. Repo: `https://github.com/iltondf/agentefin.git`.
Bot em produção: `brglobalcontas_bot`.

## Para recuperar contexto, leia (nesta ordem)

1. `docs/arquitetura/DECISAO_ARQUITETURAL_INICIAL.md`
2. `docs/arquitetura/API_BRGLOBAL.md` + `docs/arquitetura/visao-geral.md`
3. `docs/deploy/DEPLOY_DIRETO_VPS_DOCKER.md` + `docs/deploy/OPERADOR_VPS_INTERATIVO.md`
4. `docs/operacao/runbook.md` + `docs/operacao/evidencias-testes.md`
5. `docs/changelog.md` + `docs/checkpoints/`

## Governança (inegociável)

- **Ritual:** implementar → testar → documentar → checkpoint → commit local.
  **Push só com autorização explícita.**
- **Somente leitura.** O agente nunca acessa o banco direto nem escreve no
  financeiro. Fonte da verdade = BRGlobal.
- **Determinístico, 0-token-first.** LLM opcional e **desligada por padrão**.
- Sem framework agêntico / engine / orquestração. Sem Hermes. Scheduler **não ativado**.

## Operação (na VPS)

`bash scripts/ops/agentefin-vps.sh` — menu: verificar ambiente, **configurar `.env`**
(trocar token/chave/LLM sem editor), deploy/update, status, logs, reiniciar, parar,
validar `/whoami`. Atualizar após `git push`: opção **3**. Ver `OPERADOR_VPS_INTERATIVO.md`.

## Configuração

`.env` (na VPS, **gitignored**). Mínimo: `TELEGRAM_BOT_TOKEN`, `ALLOWED_USER_IDS`,
`BRGLOBAL_API_BASE_URL`, `BRGLOBAL_API_KEY`, `TZ`, `LLM_ENABLED`. Modelo: `.env.example`.

## Pendências / próximos passos

- **Opcional futuro:** avaliar rotação/revogação da chave antiga por higiene de segurança.
- (Opcional) Apagar o bot antigo `Brglobal_financeiro_bot` no BotFather.
- ⚠️ Token/chave **atuais NÃO** apareceram no chat (foram rotacionados na VPS) — os que
  vazaram (`8431551432…`, `bgf_live_ecffe92489e…`) não estão em uso.
- **Fase 2 (LLM como SELETOR DE TOOLS read-only) — PLANEJADA** (não implementada, LLM
  desligada): ver `docs/roadmap/PLANO_LLM_FASE_2.md`, `docs/arquitetura/LLM_TOOLS_DESIGN.md`,
  `docs/seguranca/LLM_GUARDRAILS.md`. Próximo: Fase 2.1 (registry de tools) só após aprovação.
- **Secretária Operacional (inbox + rascunhos c/ confirmação) — PLANEJADA** (não implementada):
  ver `docs/roadmap/PLANO_SECRETARIA_OPERACIONAL.md`, `docs/arquitetura/INBOX_OPERACIONAL_DESIGN.md`,
  `docs/seguranca/WRITE_TOOLS_GUARDRAILS.md`. Veredito: **aprovar com cuidado, faseado**; MVP = inbox textual.
- Roadmap (outros): resumos automáticos (scheduler — **não ativar sem decisão**),
  contas a receber, write com confirmação humana — exige endpoints no BRGlobal.
