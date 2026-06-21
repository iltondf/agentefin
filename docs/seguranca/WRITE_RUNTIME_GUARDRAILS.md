# Guardrails de ESCRITA em runtime — IMPLEMENTADO

Como o código impede escrita acidental. Reflete `tools_write.executar_write` + `client.post_v2`.

## Tripla trava (todas obrigatórias para POST)
1. **`settings.can_write`** = `WRITE_ENABLED=true` **E** `BRGLOBAL_WRITE_API_KEY` presente.
   - `WRITE_ENABLED=false` (padrão) → nenhum POST, em hipótese alguma.
2. **Rascunho `confirmado`** — confirmação humana explícita (`confirmar N` no Telegram).
3. **Payload válido** — `validar_payload` (obrigatórios + valor>0 + destino vale/pagamento).

Falhou qualquer uma → `ToolResult(ok=False)` **sem** chamar a rede.

## Chaves
- GET usa `read_key` (`BRGLOBAL_READ_API_KEY` ou, compat, `BRGLOBAL_API_KEY`).
- POST usa **só** `write_key` (`BRGLOBAL_WRITE_API_KEY`). `post_v2` lança `SEM_PERMISSAO` se ausente.
- A chave de leitura **nunca** é usada para escrita. Nenhuma chave aparece em log (`api_call` loga
  método/path/status/ms, nunca a chave) nem vai para a LLM.

## Idempotência
`gerar_idempotency_key(chat_id, draft_id, intent, ts_min)` → `tg:<chat>:<draft>:<intent>:<yyyymmddHHMM>`.
Estável no retry do mesmo rascunho; guardada no rascunho; sem segredo. Replay (mesma key+payload)
→ servidor devolve a mesma resposta (warning "idempotente"); payload diferente → `IDEMPOTENCY_CONFLICT`.

## Erros (client → friendly)
`AMBIGUO/NAO_ENCONTRADO/FALTA_CONTA_ORIGEM/FALTA_FORMA_PAGAMENTO/DUPLICADO_PROVAVEL/
EXCEDE_VALOR_COMBINADO/SERVICO_FINALIZADO/SEM_PERMISSAO/VALIDACAO/IDEMPOTENCY_CONFLICT/
NAO_IMPLEMENTADO` + HTTP `401/403/404/429/503/504/5xx` têm mensagem amigável. Em dúvida, não grava.

## Marcador de teste
Testes reais devem usar **`[TESTE_AGENT_READY]`** em `descricao`/`observacao`/`observacoes`.

## Estado atual (no código)
`WRITE_ENABLED=false` por padrão; `LLM_ENABLED=false` por padrão. POST real **não** executado
em produção por esta automação — depende de `WRITE_ENABLED=true` + chave write + a frase de
autorização `AUTORIZO_POST_REAL_AGENT_READY` dada pelo operador.
