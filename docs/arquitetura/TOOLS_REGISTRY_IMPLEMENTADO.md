# Registry de tools — IMPLEMENTADO

Camada única usada por comandos manuais E pela LLM (a LLM seleciona; o agente executa).

## Arquivos
- `financebot/tools.py` — `Tool`, `ToolResult`, `build_read_registry(client)`, `read_tool_names`.
- `financebot/tools_write.py` — `WriteTool`, `WRITE_TOOLS`, `validar_payload`,
  `gerar_idempotency_key`, `executar_write` (gated).
- `financebot/client.py` — `get_legacy`, `get_v2`, `post_v2` (2 envelopes).

## Cliente HTTP — 2 envelopes
- **legacy** (endpoints antigos): recurso em `envelope.data` → `get_legacy()`.
- **v2** (endpoints novos): sucesso em `envelope.data.data`; erro em `envelope.error`
  (`{ok:false,errorCode,...}`) → `get_v2()`/`post_v2()`. Erros viram `FinanceAPIError`
  com `error_code`, `candidatos`, `campos_faltando`, `precisa_confirmar`.
- Chaves: GET usa `read_key`; POST exige `write_key` (+ `Idempotency-Key`).
- Retry só em rede/429/503/504/5xx; POST nunca muda a idempotency-key.

## Read tools (21) — sem confirmação
Antigas (legacy): `consultar_whoami`, `consultar_contas_hoje/vencidas/criticas/proximos_dias`,
`consultar_resumo_diario`, `consultar_painel_operacional`.
Novas (v2): `buscar_funcionarios`, `buscar_fornecedores`, `buscar_obras`, `buscar_unidades`,
`buscar_terceirizados`, `buscar_servicos_terceirizado`, `detalhar_servico_terceirizado`,
`buscar_contas_bancarias`, `consultar_fechamento_rh`, `consultar_resumo_rh`,
`consultar_extrato_rh`, `buscar_pix`, `buscar_extrato`, `buscar_contas_pagar`.

## Write tools (6) — confirmação + Idempotency-Key + gating
`criar_lancamento_rh`, `criar_conta_pagar`, `criar_conta_pagar_paga`,
`registrar_pagamento_servico_terceirizado`, `criar_servico_terceirizado`, `cadastrar_terceirizado`.
`executar_write()` só chama POST se: `settings.can_write` (WRITE_ENABLED+chave) **E** rascunho
`confirmado` **E** payload válido. Caso contrário, retorna `ToolResult(ok=False)` sem POST.

## Comandos × LLM
Comandos antigos preservados (0 token). Buscas de debug: `/buscar_funcionario`,
`/buscar_fornecedor`, `/buscar_conta`. A LLM (parser) escolhe intent → agente roda a mesma tool.
