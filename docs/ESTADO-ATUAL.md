# ESTADO ATUAL — handoff entre sessões

> Leia primeiro ao continuar. A documentação é a fonte da verdade. Atualizado em 2026-06-21.

## Status: 🟢 AGENTE OPERACIONAL EM PRODUÇÃO (leitura + escrita confirmada)

- **Deploy:** Docker Compose **direto na VPS** (`root@srv822821`, `~/agentefin`), commit `ec19db0`.
- **Bot em produção:** **`agenteclaudio`** (token dedicado — o anterior era compartilhado com WhatsApp).
- **Container VPS:** `agentefin` **ativo** (`python -m main`, sem portas).
- **LLM:** **ligada** (`LLM_ENABLED=true`, `deepseek/deepseek-v4-flash`). **Escrita:** **ligada**
  (`WRITE_ENABLED=true` + write key). **Rascunhos:** ligados (volume `/app/data`).
- **Ciclo ponta a ponta APROVADO (2026-06-21):** Telegram → LLM → rascunho → resumo →
  **confirmação humana** → POST com Idempotency-Key → **contaPagarId 932** (paga, R$1, obs `[AGENT]`),
  recuperado só via GET agent-ready; **sem duplicidade**.
- **Scheduler:** **inexistente** (não ativar sem decisão).
- **Easypanel:** **descartado** (licença gratuita limita a 3 projetos).

## O que é

`C:\claude sistemas\agente_financeiro` — bot de Telegram (linguagem natural via LLM) que
consulta **e registra** no **BRGlobal Financeiro** via `/api/agent/v1`, **sempre** com
confirmação humana antes de qualquer POST. Stack: Python 3.12+, aiogram, httpx,
pydantic-settings. Repo: `https://github.com/iltondf/agentefin.git`. Bot: **`agenteclaudio`**.
Guardrail: *mensagem natural → LLM → rascunho → resumo → confirmação → POST com Idempotency-Key*
(**proibido** mensagem natural → POST direto). Consome **só** `/api/agent/v1` (nunca banco/SQL/Prisma).

## Para recuperar contexto, leia (nesta ordem)

1. `docs/arquitetura/DECISAO_ARQUITETURAL_INICIAL.md`
2. `docs/arquitetura/API_BRGLOBAL.md` + `docs/arquitetura/visao-geral.md`
3. `docs/deploy/DEPLOY_DIRETO_VPS_DOCKER.md` + `docs/deploy/OPERADOR_VPS_INTERATIVO.md`
4. `docs/operacao/runbook.md` + `docs/operacao/evidencias-testes.md`
5. `docs/changelog.md` + `docs/checkpoints/`

## Governança (inegociável)

- **Ritual:** implementar → testar → documentar → checkpoint → commit local.
  **Push só com autorização explícita.**
- **Escrita só com confirmação humana** (rascunho → resumo → `confirmar` → POST com
  Idempotency-Key). O agente **nunca** acessa o banco direto (sem SQL/Prisma/rotas humanas);
  consome **só** `/api/agent/v1`. Fonte da verdade = BRGlobal.
- **Determinístico, 0-token-first.** LLM como parser conversacional (ligada em produção).
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
  - **110 testes** verdes. Docs: `arquitetura/*_IMPLEMENTADO.md`, `seguranca/WRITE_RUNTIME_GUARDRAILS.md`,
    `operacao/COMO_USAR_*` (+ `COMO_USAR_LLM_TELEGRAM.md`),
    `operacao/EVIDENCIAS_AGENT_READY_{WRITE,TELEGRAM,LLM_TELEGRAM}_TESTS.md`.
  - **✅ Operacional em produção (2026-06-21):** `.env` da VPS com `LLM_ENABLED=true`,
    `WRITE_ENABLED=true`, `DRAFTS_ENABLED=true`. POST real ponta a ponta validado → **contaPagarId 932**
    (paga, R$1, `[AGENT]`), recuperado só via GET; sem duplicidade. Ver `EVIDENCIAS_AGENT_READY_LLM_TELEGRAM_TESTS.md`.
  - **Busca de contas a pagar reescrita** (servidor, commit `41198e6`): filtros+paginação+ordenação
    (default `createdAt desc`, STRICT). Tool `buscar_contas_pagar` atualizado p/ usar os filtros.
  - 🔒 **Pendências de auditoria:** rotacionar chaves expostas (Telegram antigo, write id 17, OpenRouter);
    revisar alerta web "Dados de pagamento pendentes" da #932 (cadastro bancário do fornecedor = etapa web).
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
