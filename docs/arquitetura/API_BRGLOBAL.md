# API BRGlobal — endpoints consumidos pelo agente

Contrato-alvo: **`/api/agent/v1`** (módulo `agent` do BRGlobal, read-only).
Base configurável via `BRGLOBAL_API_BASE_URL`.

## Autenticação e contrato

- **Auth:** header `Authorization: Bearer <api-key>` (formato `bgf_live_*` /
  `bgf_test_*`). Gerar no projeto financeiro: `pnpm agente:create-key`.
- **Escopos necessários (MVP):** `read:financeiro` e `read:extrato`.
- **Envelope de resposta** (todas as rotas `/api/agent/*`):
  ```json
  { "apiVersion": "v1", "generatedAt": "...", "environment": "...", "data": <payload> }
  ```
  O cliente desembrulha `data`. Em erro: `{ ..., "data": null, "error": { "error", "message", "statusCode" } }`.
- **Guardas do servidor:** kill-switch (`AGENT_API_ENABLED=false` → 503),
  rate-limit **60/min por chave**, timeout 30s (→504).

## Erros (HTTP → tratamento do cliente)

| HTTP | `kind` | Retry? | Mensagem ao usuário |
|---|---|---|---|
| 401 | auth | não | falha de autenticação |
| 403 | scope | não | sem permissão (escopo) |
| 404 | http | não | endpoint não encontrado |
| 429 | rate_limit | sim (backoff) | muitas consultas |
| 503 | disabled | não | API desabilitada |
| 504 | timeout | sim | API demorou |
| 5xx | http | sim | erro na API |
| timeout/conexão | timeout/network | sim | não consegui falar com a API |

## Endpoints

| Método | Caminho | Parâmetros | Resposta (dentro de `data`) |
|---|---|---|---|
| GET | `/whoami` | — | `{ apiKey:{id,nome,prefixo,escopos}, serverTime }` |
| GET | `/contas-pagar/hoje` | — | `{ data:[conta], total, referencia }` |
| GET | `/contas-pagar/vencidas` | — | `{ data:[conta], total, referencia }` |
| GET | `/contas-pagar/proximos-dias` | `dias` (1–90, def. 7) | `{ data:[conta], total, referencia, periodo }` |
| GET | `/contas-pagar/criticas` | — | `{ data:[conta+inteligência], total, referencia }` |
| GET | `/contas-pagar/:id` | — | dados de pagamento de uma conta |
| GET | `/resumo-diario` | — | `{ referencia, contasPagar:{vencidas,hoje,proximos7Dias,dadosPagamentoPendentes}, totais }` |
| GET | `/painel-operacional` | `contaBancariaId?`, `mes?` (YYYY-MM) | painel consolidado (ver abaixo) |
| GET | `/extrato/pendencias` | `contaBancariaId?`, `limit?`, `page?` | `{ data, total, page, limit, totalPages }` |

### Forma de uma "conta" (hermes serialize)
`{ id, descricao, fornecedorNome, fornecedorId, valorOriginal, saldoAberto,
dataVencimento, status, obraNome, unidadeNome, formaPagamentoPrevista, chavePix,
tipoChavePix, linhaDigitavel, codigoBarras, documentoUrl, dadosPagamentoPendentes }`.
Em `/criticas` acrescenta: `diasParaVencer, vencida, diasAtraso, prioridade, risco,
scorePrioridade, motivoScore, recomendacao, bucket`.

### `painel-operacional` (endpoint-mestre)
`{ referencia:{hoje,mes,contaBancariaId}, contasPagar:{vencidas:{total,valorTotalAberto,amostra},
hoje:{...}, proximos7Dias:{total,valorTotalAberto}, criticas:{total,amostra},
dadosPagamentoPendentes, totais}, caixa|null, extrato|null, matches:{fortes,provaveis},
sugestoes:{pendentes}, _observacoes:[] }`. Seções `caixa`/`extrato` vêm `null` sem
`contaBancariaId` (com aviso em `_observacoes`).

### Exemplo (real, contrato validado)
```
GET http://localhost:3334/api/agent/v1/whoami          → 401 (sem chave)
GET http://localhost:3334/health                        → 200 {"status":"ok","db":"ok"}
```

## Tabela: Comando Telegram → Endpoint

| Comando | Método cliente | Endpoint |
|---|---|---|
| `/hoje` | `contas_pagar_hoje()` | `GET /contas-pagar/hoje` |
| `/vencidas` | `contas_pagar_vencidas()` | `GET /contas-pagar/vencidas` |
| `/criticas` | `contas_pagar_criticas()` | `GET /contas-pagar/criticas` |
| `/proximos7` | `contas_pagar_proximos(7)` | `GET /contas-pagar/proximos-dias?dias=7` |
| `/painel` | `painel_operacional(contaBancariaId?)` | `GET /painel-operacional` |
| `/resumo` | `resumo_diario()` | `GET /resumo-diario` |
| `/whoami` | `whoami()` | `GET /whoami` |
| `/ajuda` | — (texto local) | — |

## Não exposto sob `/api/agent/v1` hoje (roadmap / dependência do servidor)
Contas a **receber**, `contas-pagar/inteligencia/contexto-agente` e
`financeiro-inteligencia/*` existem no servidor, mas em rotas humanas. Expor sob a
API de agentes é tarefa do time do BRGlobal (ver `docs/roadmap/fases.md`).
