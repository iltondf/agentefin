# LLM parser — IMPLEMENTADO (opcional, off por padrão)

## Arquivo
`financebot/parser.py` — `is_enabled()`, `parse(mensagem) -> dict|None`, `WRITE_INTENTS`, `_safe_json`.

## Comportamento
- `LLM_ENABLED=false` (padrão) → `is_enabled()=False`, parser nunca chamado; comportamento atual intacto.
- Habilitado: usa `OPENROUTER_API_KEY` (ou `LLM_API_KEY`) + `LLM_MODEL`, `temperature=0.1`,
  `response_format=json_object`, timeout. Saída validada por `_safe_json` (tolera blocos ```json).
- Retorno: `{intent, confidence, fields, missing, shouldAsk, question}`. **Nunca** executa,
  **nunca** recebe chave da API financeira, **nunca** inventa IDs (IDs vêm das tools de busca).

## Fluxo (commands.py `_freeform`)
1. Mensagens de pendências ("confirmar N"/"cancelar N"/"pendências") tratadas primeiro.
2. Se parser off → orienta usar /ajuda.
3. Se on → `parse()` → monta **rascunho** (não grava) → mostra resumo / pergunta o que falta.
4. Intent de consulta → orienta o comando. Intent de escrita → rascunho para confirmar.

## Segurança
Ver `docs/seguranca/LLM_PARSER_GUARDRAILS.md` e `WRITE_RUNTIME_GUARDRAILS.md`. A chave da API
financeira nunca entra no prompt; payload enviado é a frase do usuário (sem segredo).
