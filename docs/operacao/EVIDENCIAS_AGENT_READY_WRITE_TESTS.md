# Evidências — Agent-Ready (tools, rascunhos, parser) + testes

Data: 2026-06-21. Ambiente: Windows, Python 3.13 (venv).

## 1. Testes automatizados (pytest)
**51 passed.** Suítes:
- `test_client.py` / `test_client_v2.py` — unwrap legacy + v2; erro v2 (AMBIGUO); POST exige
  write key; header Bearer write + Idempotency-Key; replay idempotente; legacy preservado.
- `test_tools_registry.py` — registry tem tools antigas + novas; tool legacy/v2 chamam endpoint certo.
- `test_drafts.py` — criar/listar/detalhar/cancelar/confirmar/persistir/update.
- `test_write_gating.py` — idempotency-key estável/sem segredo; validação; **não posta sem
  WRITE_ENABLED**; **não posta sem confirmação**; posta quando tudo OK (mock).
- `test_defaults_parser.py` — defaults YAML (load/get/categoria); parser off por padrão; `_safe_json`.
- `test_config.py` / `test_formatters.py` / `test_middleware.py` — regressão (comandos antigos intactos).

Scripts: `bash -n` OK em `scripts/ops/agentefin-vps.sh` + `scripts/deploy/*.sh`.

## 2. Segurança verificada
- Nenhuma chave em arquivos rastreados (`git grep`).
- `post_v2` recusa sem write key (`SEM_PERMISSAO`); GET usa read key, POST usa write key.
- Chave nunca logada nem enviada à LLM (parser recebe só a frase do usuário).

## 3. Testes READ em produção (2026-06-21 — executados)
Base `https://lixo.brglobal.com.br/api/agent/v1`. **Somente GET (nenhum POST).**
- `GET /health` → 200 `{"status":"ok","db":"ok"}`.
- `GET /whoami` (chave de escrita, só valida escopos) → **200**, id **17**, nome **"agentetelegram"**,
  environment **production**. Escopos: read:financeiro, read:extrato, read:rh, read:terceirizados,
  read:cadastros, **write:financeiro, write:rh, write:terceirizados, write:cadastros_basico** (+ legacy).
  → a chave tem read+write; serve para GET e (quando autorizado) POST.
- `GET /contas-pagar/hoje` (legacy) → 200, envelope `data` (`{data:[],total:0,referencia}`). ✅
- `GET /cadastros/obras/buscar?nome=Rio` (v2) → 200, envelope `data.data`
  (`candidatos:[{id:4,"Residencial Rio de Janeiro"}], ambiguo:false`). ✅
- `GET /financeiro/contas-bancarias` (v2) → 200, contas sanitizadas (`ultimos4`). ✅
- **Conclusão:** parsing de 2 envelopes do cliente confere com a API real. Chave nunca foi logada/versionada.

## 4. Testes WRITE reais controlados
- **NÃO executados nesta rodada.** Falta: confirmação do backup + `BRGLOBAL_WRITE_API_KEY`
  configurada + `/whoami` write validado + frase `AUTORIZO_POST_REAL_AGENT_READY`.
- `WRITE_ENABLED` ao final desta rodada: **false**. `LLM_ENABLED` ao final: **false**.
- POST real executado: **não**.

## 5. IDs de teste criados
- Nenhum (sem POST real). Quando ocorrer, registrar aqui: intent, id criado, marcador
  `[TESTE_AGENT_READY]`, Idempotency-Key (sem segredo), resultado do replay.
