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

## 4. Testes WRITE reais controlados (2026-06-21 — EXECUTADOS)
Autorização: backup SQL confirmado pelo operador + frase `AUTORIZO_POST_REAL_AGENT_READY`.
Chave write id **17 "agentetelegram"** (env production; read+write). Todos os registros com
marcador **`[TESTE_AGENT_READY]`**, valor **R$ 1,00**, 1 por vez, sem lote, sem "confirmar tudo".
Fluxo respeitado: resolver (GET) → resumo → confirmação → POST com `Idempotency-Key`.

> **Execução técnica:** os POSTs foram feitos contra produção via HTTPS (TLS verificado pelo
> trust store do Windows), reproduzindo exatamente o contrato do `FinanceClient.post_v2`
> (Bearer write + Idempotency-Key + payload v2). O `httpx` desta máquina não fecha a cadeia TLS
> (`CERTIFICATE_VERIFY_FAILED` local; **não** ocorre na VPS Linux) — por isso a execução por
> PowerShell. Verificação TLS **nunca** foi desabilitada.

### Resolução (GET, sem efeito)
- Funcionário "Edson" → **id 10** (Edson da Conceição Ribeiro), `ambiguo:false`.
- Fornecedor "Condor" → **id 34**, `ambiguo:false`. Obra "Rio" → **id 4**.
- Conta bancária "Conta01 CEF" → **id 5**. Categoria não-mão-de-obra → **id 15** (Materiais de Construção).

### TESTE 1 — RH (`POST /rh/lancamentos`)
- Idem-Key: `tg:0:t1:criar_lancamento_rh:202606211200`
- Payload: funcionarioId 10, tipo `ajuste_positivo`, destino `pagamento`, qtd 1, valorUnit 1,
  observacao `[TESTE_AGENT_READY] ...`.
- **Resultado: 200 → `lancamentoId 291`** ("R$ 1.00 criado no pagamento").

### TESTE 2 — Conta a pagar pendente (`POST /financeiro/contas-pagar` `pago:false`)
- Idem-Key: `tg:0:t2:criar_conta_pagar:202606211200`
- fornecedorId 34, categoriaId 15, obraId 4, valor 1, vencimento 2026-06-22, descrição/obs `[TESTE_AGENT_READY]`.
- **Resultado: 200 → `contaPagarId 929`** (status pendente, saldoAberto R$ 1,00).

### TESTE 3 — Conta a pagar paga (`POST /financeiro/contas-pagar` `pago:true`)
- Idem-Key: `tg:0:t3:criar_conta_pagar_paga:202606211200`
- + contaBancariaId 5, formaPagamento pix, dataPagamento 2026-06-21.
- **Resultado: 200 → `contaPagarId 930`** (status **pago**, saldoAberto R$ 0,00 — CP + baixa oficial).

### TESTE 4 — Idempotência
- **Replay RH** (mesma key+payload) → mesmo `lancamentoId 291` + warning
  "Resposta idempotente (replay) — nada foi duplicado". Extrato RH do Edson: **só 1** lançamento #291.
- **Replay Conta** (mesma key+payload) → mesmo `contaPagarId 929` + warning idempotente.
- **Conflito** (mesma key, payload diferente: valor 2) → **409 `IDEMPOTENCY_CONFLICT`**
  ("Idempotency-Key já usada com payload diferente.").
- **Duplicidade:** nenhuma. Verificação por GET confirmou #929 (pendente) e #930 (pago) únicos.

### Erros
- Nenhum erro inesperado. Os únicos "erros" foram os **esperados** (409 conflito de idempotência — comportamento correto).

## 5. IDs de teste criados (marcador `[TESTE_AGENT_READY]`)
| Tipo | ID | Detalhe |
|---|---|---|
| RH lançamento | **291** | Edson (10), ajuste_positivo, pagamento, R$ 1,00 |
| Conta a pagar (pendente) | **929** | Condor (34), Materiais de Construção (15), obra 4, R$ 1,00, vence 22/06 |
| Conta a pagar (paga) | **930** | Condor (34), Pix, Conta01 CEF (5), R$ 1,00, status pago |

> **Limpeza:** registros de teste permanecem no banco com marcador `[TESTE_AGENT_READY]` —
> remover/estornar pelo sistema web quando desejar (o backup pré-teste cobre rollback).

## 6. Estado final / segurança
- `WRITE_ENABLED` (no `.env` do bot): **false** (os POSTs foram da etapa de teste autorizada, via
  API direta; o bot em si não foi colocado em modo escrita). `LLM_ENABLED`: **false**.
- Deploy na VPS: **não** executado nesta sessão (sem acesso SSH daqui) — pendente do operador.
- Chave nunca logada/versionada. **Recomendação: ROTACIONAR a chave id 17** (apareceu no chat).
