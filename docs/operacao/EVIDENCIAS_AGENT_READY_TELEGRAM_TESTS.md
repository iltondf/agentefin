# Evidências — Fluxo Telegram ponta a ponta (agent-ready)

Data: 2026-06-21. Ambiente: Windows, Python 3.13 (venv).

## Como foi testado
- **Unit (pytest):** `tests/test_commands_flow.py` exercita os handlers reais
  (`commands._maybe_pendencia_cmd`, `_confirmar`) com MockTransport: criar rascunho →
  corrigir → confirmar (executa POST) → cancelar → reconfirmar (não duplica) → ambiguidade.
- **E2E real (harness descartável `_verificar_telegram_e2e.py`, gitignored):** roteia a lógica
  dos handlers contra a **API de produção**, reusando as Idempotency-Keys dos testes t1/t3 →
  **replay idempotente (não cria registro novo)**.

> Observação: o **bot não foi colocado em polling** nesta sessão (sem SSH à VPS, e o token de
> produção só admite UM poller). O fluxo foi validado pelo código real dos handlers + unit
> tests + chamadas reais à API. Para usar no Telegram, fazer o deploy (comandos abaixo).

## Resultado do harness e2e (produção)
1. **Comandos antigos:** `whoami` → chave "agentetelegram" (escopos read+write); `resumo` →
   "Vencidas: 12 — R$ 25.183,22" (dados reais).
2. **Buscas:** `/buscar_funcionario Edson` → Edson (id 10); `/buscar_fornecedor Condor` → id 34.
3. **RH rascunho → detalhar → confirmar:** resolveu nome→id 10, validou, **POST** com a key do
   t1 → **lançamento #291, replay idempotente, sem duplicar**, rascunho `executado`. ✅
4. **Conta a pagar:** `corrigir N valor 1` alterou o campo; `cancelar N` → `cancelado`,
   **nenhum POST**. ✅
5. **Reconfirmar executado:** "Pendência já foi executada (sem duplicar)". ✅
6. **Conta paga (replay t3 com payload ligeiramente diferente):** retornou **IDEMPOTENCY_CONFLICT**
   (mesma key, payload diferente) → handler respondeu erro amigável, **não duplicou**. Comportamento
   correto (a 1ª gravação real do t3 = contaPagarId 930 permanece única).

## IDs (reuso por idempotência — nenhum registro novo criado nesta etapa)
- RH **#291**, Conta pendente **#929**, Conta paga **#930** (criados na etapa anterior, todos `[TESTE_AGENT_READY]`).

## Estado de configuração
- `WRITE_ENABLED`: no `.env` do bot = **false** (o harness ligou em memória só para o teste autorizado).
- `LLM_ENABLED`: **false** (sem OPENROUTER_API_KEY). Comandos manuais `/rh_teste`,`/cp_teste`,
  `/conta_paga_teste` cobrem o fluxo sem LLM.
- Deploy VPS: **não executado** (sem SSH) — comandos no §Deploy de `ESTADO-ATUAL.md`/`DEPLOY_DIRETO_VPS_DOCKER.md`.

## Endpoint de apagar/cancelar?
**Não existe** endpoint agent-ready para apagar/cancelar lançamento/conta. Portanto **nada real
foi apagado**. `cancelar N` cancela apenas o **rascunho local** (não toca no BRGlobal). Remoção
de registros de teste (#291/#929/#930) deve ser feita pelo **sistema web** ou via **restore** do backup.

## Segurança
Chave nunca logada/versionada (`git grep` limpo). **Recomendação: rotacionar a chave id 17**
(apareceu no chat). `pytest` 57 passed; `bash -n` OK nos 4 scripts.
