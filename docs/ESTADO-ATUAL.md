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
  - **Fluxo de escrita ligado:** `confirmar N` → resolve nomes→IDs (busca) → valida →
    `POST` com Idempotency-Key. Comandos manuais sem LLM: `/rh_teste`, `/cp_teste`,
    `/conta_paga_teste`, `corrigir N <campo> <valor>` (ver `RASCUNHOS_PENDENCIAS`/`COMO_USAR_*`).
  - **Validação real (2026-06-21):** POSTs reais executados com autorização — RH **#291**,
    conta a pagar **#929** (pendente) e **#930** (paga), todos `[TESTE_AGENT_READY]` R$ 1,00;
    idempotência (replay não duplica; conflito→409) confirmada. Fluxo Telegram exercitado pelos
    handlers reais (`EVIDENCIAS_AGENT_READY_TELEGRAM_TESTS.md`). **Não há endpoint de apagar** via
    agente — registros de teste removíveis só pelo web/restore.
  - **🗣️ LLM conversacional = fluxo principal:** frase livre → `parser` (JSON com `reply`/
    `calculos`/`intent`) → conversa/cálculo respondem **sem gravar**; intenção de lançar →
    rascunho → resolve (IDs+defaults) → resumo amigável → **confirmar/cancelar natural**
    ("confirmar"/"sim"/"ok"/"pode lançar" · "cancelar"/"não"). Faz contas ("soma 325+325 e lança
    pro Vanderli"→650). Modelo **`deepseek/deepseek-v4-flash`** (fallbacks qwen/gemini; vazio→gpt-4o-mini).
    `defaults.yaml` (obra 4, conta 5, categorias→15, rh.destino=pagamento) aparece no resumo.
    Ativar via `.env` (`LLM_ENABLED=true`+`OPENROUTER_API_KEY`). Ver `COMO_USAR_LLM_TELEGRAM.md`.
  - **67 testes** verdes. Docs: `arquitetura/*_IMPLEMENTADO.md`, `seguranca/WRITE_RUNTIME_GUARDRAILS.md`,
    `operacao/COMO_USAR_*` (+ `COMO_USAR_LLM_TELEGRAM.md`),
    `operacao/EVIDENCIAS_AGENT_READY_{WRITE,TELEGRAM,LLM_TELEGRAM}_TESTS.md`.
  - **Estado de config:** `.env` do bot com `WRITE_ENABLED=false`, `LLM_ENABLED=false` por padrão.
  - ⚠️ **Deploy na VPS pendente** (sem SSH nesta sessão): ver §Deploy abaixo. **Rotacionar a chave
    write id 17 "agentetelegram"** (apareceu no chat).
- Planejamento que originou (contexto): `PLANO_AGENT_READY_FASE_WRITE.md` (0008), consolidando 0006/0007.
- Roadmap (outros): resumos automáticos (scheduler — **não ativar sem decisão**), contas a receber.

## Deploy / ativar no Telegram (passos do operador na VPS)
```bash
cd ~/agentefin          # ou o diretório do clone (ex.: /opt/agentefin)
git pull --ff-only origin main
bash scripts/ops/agentefin-vps.sh
# opção 2 (configurar .env): TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS=8646895490,
#   BRGLOBAL_API_BASE_URL=https://lixo.brglobal.com.br/api/agent/v1,
#   BRGLOBAL_WRITE_API_KEY=<nova/rotacionada>, WRITE_ENABLED=true, DRAFTS_ENABLED=true,
#   DATA_DIR=/app/data, LLM_ENABLED=false (ou true + OPENROUTER_API_KEY+LLM_MODEL)
# opção 3 (deploy/update) → opção 8 e 9 (validar /whoami read e write) → testar no Telegram
```
