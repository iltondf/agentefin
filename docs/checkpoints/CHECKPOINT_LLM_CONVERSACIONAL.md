# Checkpoint 0012 — LLM conversacional (conversa + cálculo + lançamento)

**Data:** 2026-06-21.

## Objetivo
Elevar o parser de "seletor rígido de tools" para um **assistente** que conversa, calcula
contas simples e prepara rascunho — sem perder o guardrail de escrita.

## Implementado
- **`parser.py`**: saída JSON ampliada `{reply, intent, confidence, fields, calculos, missing,
  shouldAsk, question}`. `intent` inclui `conversa`/`consulta`/`pendencias`. Prompt permite
  calcular ('325+325'→650), usar o resultado como `valorUnit` quando há intenção de lançar,
  e responder conversa pura sem fields. `temperature=0.2`, `response_format=json_object`.
- **`commands._tratar_parse`**: `conversa`/`consulta`/`pendencias` respondem **sem rascunho**;
  escritas seguem rascunho→resumo→confirmação→POST. O `reply` da LLM aparece antes do resumo.
- Modelo: **`deepseek/deepseek-v4-flash`** (`.env`/`.env.example`); fallbacks documentados
  (qwen, gemini); `LLM_MODEL` vazio → `openai/gpt-4o-mini`.
- Confirmação natural ampliada ("pode lançar", "manda", além de confirmar/sim/ok).

## Guardrail (inalterado)
mensagem → LLM interpreta → rascunho → resumo → **confirmação humana** → POST (Idempotency-Key).
Proibido mensagem→POST direto. Conversa/cálculo nunca gravam.

## Testes
**67 passed** (novos: conversa não cria rascunho; cálculo→lançamento cria e pergunta destino;
reply usado). `bash -n` OK. Pipeline de escrita já validado em produção (#291/#929/#930).

## Pendente (operador, na VPS)
Ativar: `.env` `LLM_ENABLED=true`, `LLM_MODEL=deepseek/deepseek-v4-flash`, `OPENROUTER_API_KEY`
→ opção 3 (deploy) → 5 (log `llm=True`). Testar frases no Telegram (cálculo, conversa, RH,
conta paga, "confirmar"/"cancelar") e preencher `EVIDENCIAS_AGENT_READY_LLM_TELEGRAM_TESTS.md`.
A chamada LLM ao vivo não foi exercitada no dev (sem chave OpenRouter aqui). ⚠️ rotacionar chaves expostas.
