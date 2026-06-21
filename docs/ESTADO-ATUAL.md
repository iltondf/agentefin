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
- **🌟 Agent-Ready (tools + rascunhos + parser) — IMPLEMENTADO** (checkpoint 0009).
  Fonte da verdade: `BRGLOBAL_FINANCEIRO_API_AGENT_READY_2026-06-21.md` (raiz).
  - Cliente HTTP **2-envelopes** (legacy/v2); chaves **read/write separadas**; idempotência.
  - **21 read tools** (antigas+novas) + **6 write tools** com **tripla trava** (WRITE_ENABLED+chave,
    confirmação humana, payload válido). **Rascunhos SQLite** (`/app/data`, volume) + `/pendencias`.
    **Defaults** (`defaults.yaml`). **LLM parser** (JSON). **Comandos antigos preservados.**
  - **51 testes** verdes. Docs: `arquitetura/*_IMPLEMENTADO.md`, `seguranca/WRITE_RUNTIME_GUARDRAILS.md`,
    `operacao/COMO_USAR_*`, `operacao/EVIDENCIAS_AGENT_READY_WRITE_TESTS.md`.
  - **Estado de segurança:** `WRITE_ENABLED=false`, `LLM_ENABLED=false` por padrão. **POST real
    NÃO executado.** Escrita real exige: backup + `BRGLOBAL_WRITE_API_KEY` + `/whoami` write +
    frase `AUTORIZO_POST_REAL_AGENT_READY`.
- Planejamento que originou (contexto): `PLANO_AGENT_READY_FASE_WRITE.md` (0008), consolidando 0006/0007.
- Roadmap (outros): resumos automáticos (scheduler — **não ativar sem decisão**), contas a receber.
