# Checkpoint 0010 — Fluxo Telegram ligado + validação real de escrita

**Data:** 2026-06-21.

## O que mudou
- **`confirmar N` passou a EXECUTAR a escrita** (antes só marcava confirmado):
  resolve nomes→IDs (`resolve.py` via tools de busca) → valida (`tools_write.validar_payload`)
  → `POST` com Idempotency-Key → atualiza rascunho (`executado`/`erro`). Reconfirmar item
  `executado` não duplica; ambiguidade/falta de campo → volta a `pendente` e pergunta.
- **Comandos manuais (sem LLM)** para criar rascunho: `/rh_teste`, `/cp_teste`,
  `/conta_paga_teste`; `corrigir N <campo> <valor>`; `cancelar N` (não toca no BRGlobal).
- `truststore` opcional no cliente (resolve TLS local; inócuo na VPS).

## Validação real (autorizada: backup + AUTORIZO_POST_REAL_AGENT_READY)
- POSTs reais (R$ 1,00, marcador `[TESTE_AGENT_READY]`): RH **#291**, conta a pagar **#929**
  (pendente), conta a pagar **#930** (paga, Pix/CEF).
- **Idempotência:** replay (mesma key+payload) retorna o mesmo id com warning "idempotente",
  sem duplicar; conflito (mesma key, payload diferente) → **409 IDEMPOTENCY_CONFLICT**.
- **Fluxo Telegram** exercitado pelos handlers reais + 6 unit tests novos (`test_commands_flow.py`).
- Evidência: `docs/operacao/EVIDENCIAS_AGENT_READY_TELEGRAM_TESTS.md` (+ `..._WRITE_TESTS.md`).

## Apagar/cancelar registro real?
**Não existe** endpoint agent-ready de exclusão. `cancelar N` cancela só o rascunho local.
Registros de teste (#291/#929/#930) só saem pelo **sistema web** ou **restore** do backup.

## Estado
- **57 testes** verdes; `bash -n` OK. `.env` do bot: `WRITE_ENABLED=false`, `LLM_ENABLED=false`.
- **Deploy na VPS: pendente** (sem SSH nesta sessão) — passos em `ESTADO-ATUAL.md` §Deploy.
- ⚠️ **Rotacionar** a chave write id 17 "agentetelegram" (exposta no chat).

## Próximo passo
Operador: deploy na VPS (operador opção 2/3), `WRITE_ENABLED=true` + chave write nova, testar
no Telegram. Opcional: `LLM_ENABLED=true` + OPENROUTER_API_KEY para frases naturais.
