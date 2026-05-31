# Evidências de Testes

Data: 2026-05-30 (suíte/Docker) · **homologação real em PRODUÇÃO: 2026-05-31**.
Ambiente: Windows, Python 3.13.5 (venv), Node 22 / pnpm 10.

## 1. Suíte automatizada (pytest)

Comando: `.\.venv\Scripts\python.exe -m pytest -q`

Resultado: **26 passed**.

Cobertura:
- `test_config.py` — parse de `ALLOWED_USER_IDS`; LLM off por padrão; **`DEFAULT_CONTA_BANCARIA_ID` vazio → None** (regressão da auditoria).
- `test_formatters.py` — BRL/data BR; listas (vazia/cheia); críticas com
  recomendação; resumo; painel com `caixa=null` + `_observacoes`; whoami.
- `test_client.py` — desembrulho do envelope; header Bearer; 401→auth, 403→scope,
  503→disabled; **retry 429→200**; **500 esgota retries** (1+1); parse de JSON
  inválido; parâmetro `dias`; **404 não é retentado** (regressão). (Backoff neutralizado no `conftest`.)
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

## 5. Docker (auditoria final)

```
docker build -t agente-financeiro:audit .     → sucesso (imagem ~217 MB)
docker run --rm agente-financeiro:audit        → "TELEGRAM_BOT_TOKEN ausente —
                                                  encerrando (safe boot)." + log
                                                  WARNING telegram_nao_configurado
                                                  exit code 0
```

## 6. Homologação REAL contra PRODUÇÃO (2026-05-31)

- **Data/hora:** 2026-05-31, ~09:18 BRT (12:16–12:18 UTC).
- **URL:** `https://lixo.brglobal.com.br/api/agent/v1` (produção; TLS ok com AVG desligado).
- **Chave:** `bgf_live_ecffe92489e…` (id 7, "agentefinanceiro", escopos `read:financeiro, read:extrato`).

```
GET /health                  → 200 {"status":"ok","db":"ok"}
GET /api/agent/v1/whoami     → 200  ✅  (environment=production; prefixo bgf_live_ecffe92489e;
                                          escopos read:financeiro, read:extrato)
```

**Comandos testados (data-path real, via `_verificar_homologacao.py`):**

| Comando | Resultado resumido |
|---|---|
| `/whoami` | **200** — chave agentefinanceiro, escopos read:financeiro,read:extrato |
| `/hoje` | Nenhuma conta vencendo hoje ✅ |
| `/vencidas` | **7 contas — total R$ 19.420,23** (DARF R$ 4.668,98; Prefeitura R$ 601,58; DARF Previdenciário R$ 5.355,63; FGTS R$ 2.412,51; Contabilidade R$ 5.541,55; Condor R$ 180,22 e R$ 659,76) |
| `/criticas` | Nenhuma crítica ✅ |
| `/proximos7` | Nenhuma nos próximos 7 dias ✅ |
| `/resumo` | Vencidas 7 · R$ 19.420,23 · sem código de pagamento: 13 |
| `/painel` | Vencidas 7 · R$ 19.420,23 · Conciliação: matches fortes 234, prováveis 75, sugestões pendentes 19 |
| `/ajuda` | Texto local (não chama API) ✅ |

- **Dados reais confirmados:** os valores batem com o resumo automático das **05:00** do script de cron (mesma fonte de verdade). ✅
- **`/whoami` 200 confirmado.** ✅

> **Observações:**
> - O bot (`Brglobal_financeiro_bot`) está rodando **LOCALMENTE** (`python -m main` nesta máquina) — **NÃO em produção**.
> - **Pendência:** deploy no **Easypanel** (ver `docs/deploy/easypanel.md`).
> - ⚠️ **Alerta de segurança:** `TELEGRAM_BOT_TOKEN` e `BRGLOBAL_API_KEY` apareceram em texto no chat de desenvolvimento — **ROTACIONAR ambos** (BotFather `/revoke`; `agente:revoke-key` + gerar nova) antes/depois de subir.

## 7. Deploy real na VPS via Docker Compose (2026-05-31)

- **Data/hora:** 2026-05-31, ~18:41 BRT.
- **Servidor/VPS:** `root@srv822821` (VPS Hostinger). Projeto em `~/agentefin`.
- **Método:** Docker Compose **direto na VPS** (`scripts/ops/agentefin-vps.sh` → opção 3),
  **sem Easypanel**. Motivo: Easypanel gratuito limitado a **3 projetos**.
- **Sem porta exposta** (compose sem `ports`); bot por **Telegram polling** (só conexões de saída).
- **Build/up:** imagem `agentefin-agentefin` construída; container **`agentefin` `Up`**,
  `COMMAND "python -m main"`, sem portas.
- **bot_start:** confirmado — o bot responde no Telegram (polling ativo) contra
  `https://lixo.brglobal.com.br/api/agent/v1`, com `LLM_ENABLED=false` e sem scheduler.
- **Bot:** `brglobalcontas_bot` (token **rotacionado**, novo). Whitelist `ALLOWED_USER_IDS=8646895490`.

**Comandos Telegram:**

| Comando | Resultado |
|---|---|
| `/start` (= `/ajuda`) | menu/ajuda exibido ✅ (ao vivo na VPS) |
| `/painel` | PAINEL OPERACIONAL 2026-05-31: Vencidas 7 — R$ 19.420,23; Hoje 0; Próx. 7 dias 1 — R$ 529,04; Críticas 0; sem código de pagamento 13; Conciliação 234/75; sugestões 19 ✅ (ao vivo na VPS) |
| `/whoami` `/hoje` `/vencidas` `/criticas` `/proximos7` `/resumo` | disponíveis; mesmo data-path/chave de produção já validado na homologação (§6) |

- **Resumo:** agente **em produção na VPS**, respondendo com **dados reais** (consistentes com §6 e com o resumo do cron das 05:00).
- **Segredos:** não registrados nos docs (token/chave só no `.env` da VPS, gitignored).
