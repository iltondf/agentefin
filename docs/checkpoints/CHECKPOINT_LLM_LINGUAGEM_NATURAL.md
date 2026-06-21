# Checkpoint 0011 — LLM como fluxo principal (linguagem natural no Telegram)

**Data:** 2026-06-21.

## Objetivo
Tornar a **linguagem natural** o fluxo principal: o operador fala normalmente e o bot
interpreta, monta rascunho, pede o mínimo e confirma antes de gravar. Comandos técnicos
(`/rh_teste`, etc.) ficam como fallback.

## Implementado (código)
- **Parser LLM robusto** (`parser.py`): prompt cobrindo RH (diária/vale/adiantamento/ajuste),
  conta a pagar pendente e conta paga; `categoriaPalavra`; valores BR (1.800→1800); datas
  hoje/amanha; `response_format=json_object`. **Modelo fallback `openai/gpt-4o-mini`** quando
  `LLM_MODEL` vazio (`config.llm_effective_model`); `is_enabled` exige só LLM ligada + chave.
- **Confirmação/cancelamento natural** (`commands.py`): "confirmar/sim/ok" e "cancelar/não"
  sem número agem no único rascunho aberto; vários → pede o número; "pendências"/"resumo do dia".
- **Resolve + defaults** (`resolve.py`): nomes→IDs (busca), `categoriaPalavra`→categoriaId,
  obra/conta/forma padrão; lista `_defaults_usados` para o resumo.
- **Resumo amigável** (`formatters.resumo_rascunho`): rótulos PT + "Usei … padrão".
- `defaults.yaml`: obra 4, conta 5, categorias→15, rh.destinoPadrao=pagamento.

## Testes
**64 passed** (novos: parser request/parse com fallback+Bearer+json_object; confirm/cancel
natural; categoriaPalavra+defaults). `bash -n` OK. Pipeline de escrita já validado em produção
(#291/#929/#930, idempotência) nos checkpoints 0009/0010.

## Ativação (VPS — operador)
`.env`: `LLM_ENABLED=true`, `LLM_PROVIDER=openrouter`, `OPENROUTER_API_KEY=<chave>`,
`LLM_MODEL=` (fallback) — opção 2 → 3 (deploy) → 5 (log `llm=True`). A chamada LLM ao vivo
não foi exercitada nesta sessão (sem chave OpenRouter no dev); teste no Telegram (evidências).

## Estado / riscos
- `WRITE_ENABLED=true` na VPS (deploy 0010). LLM a ligar via `.env`.
- ⚠️ Rotacionar chaves expostas no chat (write + OpenRouter).
- LLM ao vivo a confirmar no Telegram (preencher `EVIDENCIAS_AGENT_READY_LLM_TELEGRAM_TESTS.md`).

## Critério de aceite
Usar o bot falando normalmente (sem comando técnico): frase → resumo → "confirmar" → grava.
