# Evidências de Testes

Data: 2026-05-30. Ambiente: Windows, Python 3.13.5 (venv), Node 22 / pnpm 10.

## 1. Suíte automatizada (pytest)

Comando: `.\.venv\Scripts\python.exe -m pytest -q`

Resultado: **24 passed**.

Cobertura:
- `test_config.py` — parse de `ALLOWED_USER_IDS`; LLM off por padrão.
- `test_formatters.py` — BRL/data BR; listas (vazia/cheia); críticas com
  recomendação; resumo; painel com `caixa=null` + `_observacoes`; whoami.
- `test_client.py` — desembrulho do envelope; header Bearer; 401→auth, 403→scope,
  503→disabled; **retry 429→200**; **500 esgota retries** (1+1); parse de JSON
  inválido; parâmetro `dias` em proximos-dias. (Backoff neutralizado no `conftest`.)
- `test_integration.py` — **over-the-wire real**: stub HTTP local com o mesmo
  envelope da API → cliente → formatter (`Energia SA`, `R$ 150,00`).
- `test_middleware.py` — whitelist nega desconhecido; permite listado; rate limit.

## 2. Prisma Client (problema do ambiente resolvido)

```
> pnpm run db:generate
✔ Generated Prisma Client (v5.22.0)
```

## 3. API real do financeiro (read-only, sem mutação)

API 28-05 (com `/api/agent/v1`) subida em `:3334`:

```
GET /health                                 → 200 {"status":"ok","version":"0.1.0","db":"ok"}
GET /api/agent/v1/whoami            (s/chave)→ 401   (contrato de agente real)
GET /api/agent/v1/contas-pagar/hoje (chave inválida) → 401
```

API 16-05 (referência citada, sem módulo agent) em `:3333`:
```
GET /api/agent/v1/whoami                     → 404   (versão sem API de agentes)
```

## 4. Cliente Python contra a API real (degradação ponta a ponta)

```
-> GET http://localhost:3334/api/agent/v1/contas-pagar/hoje  (key=nao)
Degradacao OK — erro tratado: kind=auth status=401
Mensagem ao usuario: 🔒 Falha de autenticação com a API financeira (chave inválida ou ausente).

-> GET http://localhost:59999/api/agent/v1/contas-pagar/hoje  (rede indisponível)
Degradacao OK — erro tratado: kind=network status=None
Mensagem ao usuario: 📡 Não consegui falar com a API financeira agora.
```

## 5. Não validado (restrição da tarefa)

Resposta **200 autenticada com dados reais** exige API Key (`bgf_*`), cujo registro
é um **INSERT** (proibido — BRGlobal read-only). Passo do operador: gerar a chave
(`pnpm agente:create-key`), definir `BRGLOBAL_API_KEY`/`BRGLOBAL_API_BASE_URL`,
rodar `/whoami`.
