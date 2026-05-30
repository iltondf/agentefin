# Fluxo — comando → resposta

```
/hoje
  │
  ▼
AccessMiddleware  ── uid ∈ ALLOWED_USER_IDS? ── não → silêncio
  │ sim                                       ── rate limit? → "aguarde"
  ▼
Command Router (commands._hoje)
  │  client.contas_pagar_hoje()
  ▼
Finance API Client
  │  GET {BASE}/contas-pagar/hoje   (Bearer)
  │  timeout / retry (transitórios) / classifica status
  ▼
BRGlobal /api/agent/v1   →  envelope { ..., data: { data:[...], total, referencia } }
  │  _unwrap → data
  ▼
formatters.hoje(data)   (texto puro, 0 token)
  ▼
message.answer(texto)
```

## Caminhos de erro (degradação)
- 401 → "🔒 Falha de autenticação…"  | 403 → "🔒 sem permissão…"
- 429 → retry/backoff; persistindo → "⏳ muitas consultas…"
- 503 → "🚫 API desabilitada"        | timeout/rede → "⌛/📡 …"
- exceção inesperada → "⚠️ erro inesperado" (logado, sem stacktrace ao usuário)

## Texto livre
Sem LLM (padrão): "use /ajuda". Com LLM: usa `resumo-diario` como contexto e
`llm.answer_freeform` (degrada para "/ajuda" se a LLM falhar).
