# Evidências — LLM + linguagem natural no Telegram

Data: 2026-06-21.

## Configuração
- Modelo escolhido: **`deepseek/deepseek-v4-flash`** (fallbacks: `qwen/qwen3.5-flash-02-23`,
  `google/gemini-2.5-flash-lite`). Se `LLM_MODEL` vazio → `openai/gpt-4o-mini`.
- Provider: openrouter; chave via `OPENROUTER_API_KEY` (segredo, não versionado).
- **Modo conversacional:** parser devolve `reply`/`calculos`/`intent` (inclui `conversa`).
  Conversa e cálculo **não** criam rascunho; só intenção de lançar + confirmação grava.
- Defaults (`defaults.yaml`): obra **4**, conta **5**, forma **pix**, categorias areia/material/
  ferramenta/… → **15**, `rh.destinoPadrao=pagamento`.

## O que foi validado (código + testes)
- **110 testes** (pytest) incluindo: parser monta request correto (modelo fallback, Bearer
  OPENROUTER, `response_format=json_object`) e parseia o JSON; confirmação/cancelamento natural
  (sem número) agindo no único rascunho; `categoriaPalavra`+defaults na resolução; gating de escrita.
- **Fluxo natural** ligado no router: qualquer texto livre (não-comando, não-pendência) →
  `parser.parse` → rascunho → resolve (IDs+defaults) → **resumo** → confirmar/cancelar natural.
- Pipeline de escrita já validado em produção (POSTs reais #291/#929/#930, idempotência).

> A chamada **LLM ao vivo** depende da `OPENROUTER_API_KEY` (configurada na VPS, não nesta
> máquina de dev). Validação ao vivo = etapa no Telegram (abaixo).

## Testes a fazer no Telegram (VPS, após `llm=True`)
| Frase | Esperado |
|---|---|
| `[TESTE_AGENT_READY] Edson fez uma diária de R$ 1 no pagamento hoje` | resumo RH → "confirmar" → lançamento criado |
| `[TESTE_AGENT_READY] Edson fez uma diária de R$ 1 hoje` | usa destino padrão "pagamento" (mostra no resumo) |
| `[TESTE_AGENT_READY] lança uma conta de R$ 1 para Condor para amanhã` | conta pendente, categoria 15/obra 4 default → confirmar |
| `[TESTE_AGENT_READY] comprei ferramenta de R$ 1 no fornecedor Condor e paguei no Pix hoje` | conta paga (conta 5, pix) → confirmar |
| `[TESTE_AGENT_READY] comprei uma ferramenta de R$ 1 hoje` | pergunta "Qual foi o fornecedor?" |
| `pendências` | lista rascunhos |
| `confirmar` / `cancelar` | age no único rascunho aberto |

## ✅ Resultado ao vivo (bot `agenteclaudio`, produção — 2026-06-21)
Estado: **llm=True, write=True, drafts=True**. Modelo `deepseek/deepseek-v4-flash`.

Frases naturais testadas (rascunhos #13–#18, só resumo — **sem confirmar**):

| # | Frase | Interpretação correta |
|---|---|---|
| 13 | "comprei fio na ligar por 75,26 vence dia 25/06" | **Conta a pagar (pendente)** · venc **2026-06-25** · sem "Pago em" |
| 14 | "comprei cimento por 60 na Condor pela conta 2" | **Conta paga** · Pago hoje · **conta 6** (conta 2) |
| 15 | "comprei 11 cabos de vassoura por 35 na Ligar" | Conta paga · Pix · conta 5 · cat 15 |
| 16 | "comprei disco de corte na condor por 20 reais" | Conta paga · **categoria padrão 15** (sem palavra) |
| 17 | "paguei 300 ... conserto do elevador na carlos peças" | **Paga** ("paguei") · fornecedor **Outros (6)** + `[AJUSTAR FORNECEDOR: Carlos Peças]` |
| 18 | "anotar areia p/ império das areias para o dia 26/06/26" | **Pendente** · venc **2026-06-26** · pediu o valor faltante → "1500" (slot-fill) |

Confirmado: datas determinísticas (texto > LLM), conta paga vs pendente, conta 1/2 → 5/6,
Pix padrão, categoria padrão, fornecedor Outros com `[AJUSTAR FORNECEDOR]`, slot-fill de valor.
Pergunta duplicada do slot-fill **corrigida** (commit `ec19db0`).

## ✅ POST real ponta a ponta (Telegram → BRGlobal)
- Frase: **`[TESTE_AGENT_READY] comprei um item de teste por R$ 1 na Ligar`** → resumo → **`confirmar`**.
- Ciclo: **Telegram → LLM → rascunho → resumo → confirmação humana → POST (Idempotency-Key) → conta paga**.
- Conta criada no BRGlobal e recuperada **só via GET agent-ready** (sem banco/SQL/Prisma):
  `GET /financeiro/contas-pagar/buscar?status=pago&fornecedorId=33&valor=1&dataPagamento=2026-06-21&orderBy=createdAt&order=desc`

| Campo | Valor |
|---|---|
| **contaPagarId** | **932** |
| fornecedor | LIGAR(Walace) — id 33 |
| descrição | item de teste |
| valor / pago / saldo | R$ 1,00 / R$ 1,00 / **R$ 0,00** |
| status | **pago** |
| vencimento / pagamento | 2026-06-21 / 2026-06-21 |
| categoria / obra | 15 (Materiais de Construção) / 4 (Residencial Rio de Janeiro) |
| observações | **`[AGENT]`** (assinatura do agente) |
| createdAt | 2026-06-21T18:58:55Z |

- **Duplicidade: não.** `q=AGENT` (pagas) retorna só **932** (novo) e **930** (teste Condor anterior).
  Histórico de escrita do agente: **#291** (RH), **#929** (pendente), **#930** (paga), **#932** (paga, este teste).
- **Rascunhos #13–#18:** testes de resumo, **nunca confirmados → nenhum POST** (comprovado: o GET
  só lista 929/930/932 com `[AGENT]`). Cancelados no Telegram (`cancelar N`, sem efeito no BRGlobal).

## API agent-ready: busca de contas a pagar reescrita (lado servidor)
A versão anterior do `GET /financeiro/contas-pagar/buscar` ignorava paginação/ordenação e não
alcançava contas pagas recentes (caía em 50 itens fixos / inteligência de contas abertas). Foi
**reescrita em produção (commit servidor `41198e6`, sem migration)** com filtros reais
(`status, fornecedor, fornecedorId, valor, dataVencimento, dataPagamento, criadoEmDe/Ate, q,
observacao, obraId`), **paginação** (`page`, `limit` 1–200, `hasMore`, `total`) e **ordenação**
(`orderBy=createdAt|dataVencimento|dataPagamento|valor|id`, `order=asc|desc`, default `createdAt desc`).
Validação **STRICT** (param desconhecido → 422 `VALIDACAO`). Resultado no aninhamento `data.data.candidatos`.
- **Bot atualizado:** tool `buscar_contas_pagar` repassa esses filtros e usa `createdAt desc` por padrão
  (descarta params fora do whitelist p/ evitar 422). Cobertura em `tests/test_tools_registry.py`.

## Fora do escopo de hoje (NÃO validado — não tratar como concluído)
RH via Telegram (lançamento/vale vs pagamento/diárias/produção), terceirizados (serviço/
pagamento) e áudio/Whisper **não** foram validados nesta sessão. Próxima fase = **RH**
(ver `docs/roadmap/ROADMAP_RH_E_WHISPER.md`).

## Pendências futuras (auditoria)
- ⚠️ Alerta visual **"Dados de pagamento pendentes"** na conta #932 no web — revisar no fechamento
  (não impede o registro; cadastro de dados bancários do fornecedor é etapa do web).
- 🔒 **Rotacionar chaves expostas no chat** (Telegram token antigo, write key id 17, OpenRouter).

## Segurança
Chave OpenRouter e write nunca logadas/versionadas. GET de contas a pagar **não** retorna dados
bancários sensíveis (conta/agência/dígito/PIX). **Rotacionar** chaves expostas no chat.
