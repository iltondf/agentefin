# BRGlobal Financeiro — API Agent-Ready

> Documento auto-contido para o **projeto externo do Agente Financeiro** adaptar o bot existente à API
> agent-ready do sistema financeiro. Data: 2026-06-21. Fonte: código real de `apps/api/src/modules/agent/*`
> e docs do repositório financeiro (`docs/api/AGENT_API.md`, `CHECKPOINT_AGENT_API_FASE_C_D.md`,
> `PLANO_AGENT_READY.md`). **Sem segredos.** Onde algo não puder ser confirmado, está marcado
> **(confirmar no código)**.

---

## 1. Objetivo do documento

- O **Agente Financeiro já existe** (bot Telegram, hoje read-only).
- O sistema financeiro evoluiu e agora expõe uma API mais completa (consulta + **inclusão segura**).
- O agente deve consumir **somente** `https://lixo.brglobal.com.br/api/agent/v1`.
- O agente **NÃO** deve acessar banco, Prisma, SQL nem rotas humanas (cookie/JWT).
- **A API financeira é a fonte da verdade.** Toda regra de negócio (validação, categoria, obra, saldo,
  baixa, idempotência, auditoria) acontece no servidor; o agente apenas orquestra e confirma.

## 2. Estado atual em produção

- **URL pública:** `https://lixo.brglobal.com.br`
- **Base da API do agente:** `https://lixo.brglobal.com.br/api/agent/v1`
- **Autenticação:** `Authorization: Bearer <BRGLOBAL_API_KEY>` (a chave **não** vai neste documento).
- **Produção atualizada** com agent-ready (release único, commit `e5bf794`, 3 migrations aditivas aplicadas).
- **Health esperado:** `GET https://lixo.brglobal.com.br/health` → `{"status":"ok","db":"ok"}`.
- **Observação operacional:** logo após o deploy houve **travamento do Passenger/lsnode** (health em
  timeout) — resolvido com `touch tmp/restart.txt`. **Não era erro de banco** (o banco chegou a ser
  substituído manualmente e o erro persistiu até o restart). Relevante só para quem opera o deploy do
  financeiro; **não afeta o agente**.

## 3. Contrato geral da API

- **Base path:** `/api/agent/v1`. **Content-Type:** `application/json`.
- **Envelope externo (TODAS as respostas):**
  ```json
  { "apiVersion": "v1", "generatedAt": "<ISO-8601>", "environment": "production",
    "data": { /* sucesso */ } , "error": { /* em erro: data=null */ } }
  ```
- **Endpoints ANTIGOS** (seção 5): `data` é o payload "cru" (ex.: `{ "data": [...], "total": 12 }`).
- **Endpoints NOVOS** (seções 6 e 7): `data`/`error` seguem um formato padronizado **aninhado**:
  - Sucesso → `envelope.data = { "ok": true, "data": { /* recurso */ }, "message": "...", "warnings": [], "nextAction": null }`
    → ou seja, o recurso real fica em **`envelope.data.data`**.
  - Erro/confirmação → `envelope.error = { "ok": false, "errorCode": "...", "precisaConfirmar": false,
    "message": "...", "candidatos": [], "camposFaltando": [] }`.
- **Headers obrigatórios:** `Authorization: Bearer <chave>`, `Content-Type: application/json` (em POST).
- **Headers opcionais:** `Idempotency-Key` (**recomendado/obrigatório na prática** para todo POST — seção 8).
- **GET = read-only** (sem efeito colateral). **POST = escrita** (cria dado real).
- **Rate limit (confirmado no código):** **60 req/min por chave** nos GET; **20 req/min por chave** nos POST.
  Excedeu → HTTP **429**.
- **Timeout do servidor:** ~30s por requisição (`AGENT_REQUEST_TIMEOUT_MS`, default 30000). Acima disso o
  servidor responde **504**. **Recomendação no agente:** timeout de cliente ~30–35s; **retry** só em
  429/503/504/erros de rede, com backoff; **POST só pode ser re-tentado com a MESMA `Idempotency-Key`**.
- **Kill-switch:** se `AGENT_API_ENABLED=false` no servidor, toda `/api/agent/*` responde **503**.

## 4. Escopos

Definidos em `agent.types.ts`. Cada rota exige um escopo via `requireEscopo(...)` (uma rota aceita 2 via
`requireQualquerEscopo(...)`). Faltando escopo → **403 `SEM_PERMISSAO`**.

### 4.1 Leitura (todos ativos)
- `read:financeiro` · `read:extrato` · `read:rh` · `read:terceirizados` · `read:cadastros`
- ⚠️ **Não existe `read:fornecedores`** — a busca de fornecedores usa **`read:financeiro`** (confirmado no código).

### 4.2 Escrita (todos ativos)
- `write:financeiro` · `write:rh` · `write:terceirizados` · `write:cadastros_basico`
- Compatibilidade (placeholders antigos, mantidos mas **sem rota**): `write:contas`, `write:despesa-paga`,
  `write:baixas`, `write:treinamento`, `notify:resumo`.

### 4.3 Regras de chave
- **A chave read-only atual do agente NÃO deve ganhar escopo write automaticamente.**
- Para escrita: **criar chave nova** (ou atualizar escopos de forma controlada) — gestão em
  `/admin/api-keys` (UI humana) ou CLI `pnpm --filter @financeiro-v2/database agente:create-key`.
- **Nunca** expor a chave no prompt da LLM. **Nunca** logar a chave completa (no máximo o prefixo).

## 5. Endpoints ANTIGOS preservados (continuam funcionando)

Todos GET. `data` = payload cru (sem `ok/message`).

| Método | Path | Escopo | Query | Finalidade | Comando antigo |
|---|---|---|---|---|---|
| GET | `/whoami` | *(nenhum, só Bearer)* | — | valida a chave; retorna `{ apiKey:{id,nome,prefixo,escopos}, serverTime }` | `/whoami` |
| GET | `/contas-pagar/hoje` | `read:financeiro` | — | contas que vencem hoje `{data:[],total}` | `/hoje` |
| GET | `/contas-pagar/vencidas` | `read:financeiro` | — | contas vencidas | `/vencidas` |
| GET | `/contas-pagar/proximos-dias` | `read:financeiro` | `dias` (1–90, default 7) | próximas N dias | `/proximos7` |
| GET | `/contas-pagar/criticas` | `read:financeiro` | — | contas em prioridade crítica/alta | `/criticas` |
| GET | `/contas-pagar/:id` | `read:financeiro` | `:id` | detalhe/dados de pagamento de 1 conta | — |
| GET | `/resumo-diario` | `read:financeiro` | — | snapshot leve (vencidas+hoje+prox7+totais+pendentes) | `/resumo` |
| GET | `/painel-operacional` | `read:financeiro` | `contaBancariaId`, `mes` (YYYY-MM) | painel agregado (pesado — usar p/ 1 snapshot, **não** em loop) | `/painel` |
| GET | `/extrato/pendencias` | `read:extrato` | `contaBancariaId`, `limit` (1–200, default 50), `page` | extrato pendente paginado | — |

## 6. Novos endpoints de LEITURA / RESOLVE (Fase C)

Todos GET. Resposta padronizada → recurso em **`envelope.data.data`**. Reaproveitam services oficiais.

| Método | Path | Escopo | Query | Finalidade / campos principais |
|---|---|---|---|---|
| GET | `/rh/funcionarios/buscar` | `read:rh` | `nome` (obrigatório) | candidatos `{id,nome,cargo,status,tipoVinculo,tipoPagamento,recebeVale,obraDefaultId,temPix}` + `total,ambiguo` |
| GET | `/terceirizados/buscar` | `read:terceirizados` | `nome` (obrigatório) | candidatos `{funcionarioId,nome,cargo,servicosAbertos,servicosPrincipais[]}` + `total,ambiguo` |
| GET | `/terceirizados/:funcionarioId/servicos` | `read:terceirizados` | `:funcionarioId`, `status?` (aberto\|finalizado\|cancelado) | `{servicos:[...],total}` (cada serviço já com saldo) |
| GET | `/terceirizados/servicos/buscar` | `read:terceirizados` | `nome` (obrigatório), `status?` | serviços por nome do terceirizado `{servicos,total,terceirizadosEncontrados}` |
| GET | `/terceirizados/servicos/:id` | `read:terceirizados` | `:id` | detalhe: `{id,terceirizado,descricao,obra,unidades[],status,valorCombinado,totalPago,saldoRestante,excedente,situacao,pagamentos[]}` |
| GET | `/financeiro/contas-pagar/buscar` | `read:financeiro` | `fornecedor?`, `status?`, `obraId?` | resolve CP por fornecedor → `{candidatos,total,ambiguo}` (ou lista por filtro) |
| GET | `/financeiro/fornecedores/buscar` | `read:financeiro` | `nome` (obrigatório) | candidatos `{id,nome,tipoFornecedor,status,categoriaPadraoId,temPix}` + `total,ambiguo` |
| GET | `/financeiro/contas-bancarias` | `read:financeiro` | — | **sanitizado** `{contas:[{id,apelido,banco,tipo,ativa,ultimos4}],total}` |
| GET | `/financeiro/contas-bancarias/buscar` | `read:financeiro` | `nome` (obrigatório) | idem, filtrado por apelido/banco |
| GET | `/cadastros/obras/buscar` | `read:cadastros` | `nome` (obrigatório) | candidatos `{id,codigo,nome,status}` + `total,ambiguo` |
| GET | `/cadastros/obras/:id/unidades` | `read:cadastros` | `:id` | `{obraId,unidades:[{id,codigo,nome,status}],total}` |
| GET | `/rh/fechamento` | `read:rh` | `mes` (YYYY-MM), `tipo` (vale\|pagamento) | preview do fechamento (totais + funcionários) |
| GET | `/rh/fechamento/funcionario` | `read:rh` | `funcionarioId`, `mes`, `tipo` | preview de 1 funcionário (líquido, compensação do vale) |
| GET | `/rh/resumo` | `read:rh` | `funcionarioId`, `mes` (YYYY-MM) | lançamentos do mês agrupados em `vale[]`/`pagamento[]` (markers técnicos já removidos) |
| GET | `/rh/extrato` | `read:rh` | `funcionarioId`, `mes` | extrato do mês do funcionário |
| GET | `/extrato/pix/buscar` | `read:extrato` | `valor?`, `data?` (YYYY-MM-DD), `nome?`, `contaBancariaId?` | Pix candidatos (filtro de valor pós-query) |
| GET | `/extrato/buscar` | `read:extrato` | `valor?`, `data?`, `contaBancariaId?` | transações bancárias candidatas |

**Cuidados de desambiguação:** quando `ambiguo=true` ou `candidatos.length>1`, o agente **deve perguntar
qual** antes de qualquer escrita. Para pagamento de serviço, sempre resolver **terceirizado → serviço
aberto** (pode haver mais de um serviço) antes de pagar.

> **Segurança de dado:** contas bancárias expõem só `ultimos4` (nunca conta/agência/dígito completos).

## 7. Novos endpoints de ESCRITA controlada (Fase D)

Todos POST. **Exigem escopo write + (na prática) `Idempotency-Key` + confirmação humana no agente.**
Reaproveitam os services oficiais (sem regra nova). Recurso criado em `envelope.data.data`.

> **REGRA TRANSVERSAL (todas as escritas):**
> - O agente **só chama POST após confirmação humana explícita** do usuário.
> - **Não** escrever só porque a LLM "entendeu" a frase.
> - Se houver **ambiguidade** (`AMBIGUO`/`candidatos`), **perguntar antes**.
> - Se faltar **obra/categoria/conta/forma de pagamento** (`camposFaltando`), **pedir o complemento** ou
>   manter rascunho no lado do agente — **não forçar gravação**.

### 7.1 Registrar pagamento de serviço terceirizado
`POST /terceirizados/servicos/:id/pagamentos` · escopo **`write:terceirizados`**
Reusa `registrarPagamentoServico` → cria **Conta a Pagar já paga + baixa oficial** vinculada ao serviço.
```json
{ "valor": 300, "dataPagamento": "2026-06-21",
  "tipo": "adiantamento",            // adiantamento|pagamento_parcial|pagamento_final|extra_autorizado|material_reembolso
  "formaPagamento": "pix",           // pix|transferencia|dinheiro|outro
  "contaBancariaId": 5,              // OBRIGATÓRIO
  "observacao": "adiantamento elétrica",
  "excedenteAutorizado": false, "motivoExcedente": null,
  "confirmarDuplicado": false }
```
- **Validações/efeitos:** conta obrigatória; forma obrigatória; **serviço precisa ter obra** (a CP herda a
  obra do serviço — sem obra → bloqueia); categoria = **"Mão de Obra"**; respeita saldo/valor combinado.
- **Resposta (`data.data`):** `{servicoId,contaPagarId,pagamentoContaPagarId,valorPago,totalPagoServico,saldoRestante,excedente,status}`.
- **Erros:** `FALTA_CONTA_ORIGEM`, `FALTA_FORMA_PAGAMENTO`, `SERVICO_FINALIZADO`, `EXCEDE_VALOR_COMBINADO`
  (`precisaConfirmar` → reenviar `excedenteAutorizado:true`+`motivoExcedente`), `DUPLICADO_PROVAVEL`
  (reenviar `confirmarDuplicado:true`).

### 7.2 Criar Conta a Pagar (pendente OU já paga)
`POST /financeiro/contas-pagar` · escopo **`write:financeiro`** · reusa `createContaPagar`.
```json
{ "fornecedorId": 12, "categoriaId": 16, "obraId": 4, "obraUnidadeId": null,
  "descricao": "Material elétrico", "valor": 180, "dataVencimento": "2026-06-21",
  "dataCompetencia": null, "observacoes": "incluído via agente",
  "pago": false,                      // true = já paga
  "contaBancariaId": null, "formaPagamento": null, "dataPagamento": null,
  "confirmarDuplicado": false }
```
- Se `pago:true` → **exige** `contaBancariaId` + `formaPagamento` + `dataPagamento` (cria CP + baixa oficial).
- **Mão de Obra exige obra:** se `categoriaId` for a categoria "Mão de Obra", `obraId` é obrigatório.
- Anti-duplicidade: fornecedor+valor+vencimento+descrição → `DUPLICADO_PROVAVEL`.
- **Resposta:** `{contaPagarId,status,valorOriginal,pago}`. **Não** permite alterar/cancelar CP paga.

### 7.3 Criar lançamento RH (produção/tarefa/diária/adiantamento)
`POST /rh/lancamentos` · escopo **`write:rh`** · reusa `createRhLancamento`.
```json
{ "funcionarioId": 33,
  "tipo": "tarefa",                   // falta|diaria_extra|tarefa|inss_informado|adiantamento|ajuste_positivo|ajuste_negativo
  "destino": "vale",                  // vale|pagamento (opcional; traduzido p/ markers internos)
  "data": "2026-06-21", "qtd": 3, "valorUnit": 100,
  "obraId": 4, "obraUnidadeId": 18, "servicoTabelaPrecoId": null,
  "observacao": "produção via agente", "confirmarDuplicado": false }
```
- O agente **não** conhece markers técnicos — só envia `destino`. Anti-duplicidade: funcionário+data+tipo+valor.
- **Resposta:** `{lancamentoId,funcionarioId,tipo,destino,qtd,valorUnit,valor,data}`. **Não** edita/exclui lançamento antigo.

### 7.4 Criar serviço de terceirizado
`POST /terceirizados/servicos` · escopo **`write:terceirizados`** · reusa `createServicoTerceirizado`.
```json
{ "funcionarioId": 33, "descricao": "Elétrica duplex 21,22", "valorCombinado": 2500,
  "obraId": 4,                        // OBRIGATÓRIO (serviço de mão de obra precisa de obra)
  "obraUnidadeIds": [21,22], "dataInicio": "2026-06-21", "dataPrevisaoFim": "2026-07-10",
  "observacoes": "criado via agente", "confirmarDuplicado": false }
```
- Funcionário deve ser **terceirizado**; obra existe; unidades pertencem à obra. Anti-duplicidade: funcionário+descrição+obra+valor.
- **Resposta:** `{servicoId,funcionarioId,valorCombinado,status}`. **Não** altera valor combinado / finaliza / cancela via agente.

### 7.5 Cadastrar terceirizado rápido
`POST /terceirizados` · escopo **`write:terceirizados` OU `write:cadastros_basico`** · reusa `cadastrarTerceirizado`.
```json
{ "nome": "Carlos Eletricista", "funcao": "Eletricista", "cpfCnpj": null,
  "telefone": null, "chavePix": null, "obraDefaultId": 4, "confirmarDuplicado": false }
```
- Reaproveita por CPF/CNPJ. Sem CPF e nome parecido existente → `AMBIGUO` (candidatos) → reenviar
  `confirmarDuplicado:true` para criar novo. Só cadastra (não cria serviço/lançamento/CP).
- **Resposta:** `{funcionarioId,entidadeId,nome,reused}`.

### 7.6 Fechamento RH → Conta a Pagar (BLOQUEADO)
`POST /rh/fechamento/conta-pagar` · escopo `write:rh` → **retorna 501 `NAO_IMPLEMENTADO`**.
Fechamento de folha em CP é ação sensível: **fica no sistema web**. O agente deve orientar o usuário a usar o web.

## 8. Idempotência (`Idempotency-Key` + tabela `agent_idempotency`)

- Header **`Idempotency-Key`** — **enviar em todo POST** (recomendado/obrigatório na prática).
- O servidor reserva por `(apiKeyId, idempotencyKey)` e cacheia a resposta:
  - **Replay** (mesma chave + **mesmo payload**) → devolve a **mesma resposta**, **sem duplicar** (vem com
    `warnings: ["Resposta idempotente (replay) — nada foi duplicado."]`).
  - **Conflito** (mesma chave + **payload diferente**) → **409 `IDEMPOTENCY_CONFLICT`**.
  - Falha do service → reserva é apagada (permite novo retry). TTL 24h.
- Além disso há guard de **"duplicado provável"** por recurso → `DUPLICADO_PROVAVEL` (contornável com `confirmarDuplicado:true`).
- **Recomendação do agente:** gerar a chave **por AÇÃO CONFIRMADA**, não por mensagem solta. Exemplo:
  `telegram:<chat_id>:<message_id>:<acao>:<yyyymmddHHMM>` (ou outro formato estável que **não mude no retry**).
- **Nunca** salvar segredo/token na key.

## 9. Auditoria (tabela `agent_action_logs`)

- Cada escrita grava: `apiKeyId`, `action` (ex.: `terceirizado.pagamento`, `contas-pagar.criar`,
  `rh.lancamento`, `terceirizado.servico.criar`, `terceirizado.cadastrar`), `resourceType`, `resourceId`,
  `status` (ok/erro), `errorCode`, `requestSummary` (**resumo seguro — campos sensíveis mascarados**),
  `resultSummary`, `idempotencyKey`, `createdAt`.
- **Origem da escrita:** services que aceitam `criadoPor` recebem **`agent:<apiKeyId>`** (serviço/pagamento
  de terceirizado). Onde o modelo não tem `criadoPor` (Conta a Pagar, lançamento RH), fica o marcador
  discreto **`[AGENT]`** na observação + o registro em `agent_action_logs`.
- **Limitação documentada:** **não** há valor `agente` no enum `OrigemLancamento`; CP do agente fica
  `origem=manual` (rastro via `[AGENT]` + log). Não afeta o consumo pelo agente.
- **Nunca** logar token/chave completa nem payload sensível completo (o servidor já mascara).

## 10. Regras de segurança para o agente

**O agente PODE:** consultar dados; resolver IDs (Fase C); montar rascunhos; pedir confirmação; **executar
escrita somente após confirmação humana explícita**; usar apenas `/api/agent/v1`.

**O agente NÃO PODE:** acessar banco direto · usar Prisma · usar SQL · usar rotas humanas (cookie/JWT) ·
inventar fornecedor/funcionário/obra/conta bancária · lançar pagamento sem confirmação · baixar a conta
errada · repetir POST sem `Idempotency-Key` · ocultar erro da API do usuário · transformar dúvida em
gravação · usar chave read-only para write · colocar segredo no prompt da LLM.

## 11. Fluxos recomendados

### 11.1 Consulta simples — "o que vence hoje?"
→ `GET /contas-pagar/hoje` (ou `/resumo-diario`) → responder com resumo. **Sem confirmação.**

### 11.2 Criar Conta a Pagar — "lança uma conta de 500 da Condor para amanhã"
1. `GET /financeiro/fornecedores/buscar?nome=Condor` (se `ambiguo` → perguntar).
2. Resolver categoria/obra se necessário (se for mão de obra, obra é obrigatória).
3. Montar resumo e **pedir confirmação**.
4. Após confirmar → `POST /financeiro/contas-pagar` com `Idempotency-Key`.
5. Responder com o `contaPagarId` criado.

### 11.3 Registrar pagamento de serviço — "paguei 400 para Jailton da elétrica no Pix pela Caixa"
1. `GET /terceirizados/buscar?nome=Jailton` (se >1 → perguntar).
2. `GET /terceirizados/:funcionarioId/servicos?status=aberto` (se >1 serviço → perguntar qual).
3. `GET /financeiro/contas-bancarias/buscar?nome=Caixa` → resolver `contaBancariaId`.
4. Confirmar valor/forma/serviço/obra com o usuário.
5. `POST /terceirizados/servicos/:id/pagamentos` (com `Idempotency-Key`).
6. Informar CP criada/baixada + `saldoRestante` do serviço.
   > "Caixa" = conta bancária da **Caixa Econômica Federal (CEF)** já cadastrada — **não** criar conta nova.

### 11.4 Criar lançamento RH — "lança diária do João na obra Rio de Janeiro"
1. `GET /rh/funcionarios/buscar?nome=João` (se >1 → perguntar).
2. `GET /cadastros/obras/buscar?nome=Rio de Janeiro` → `obraId`.
3. Validar tipo/valor/data → **confirmar** → `POST /rh/lancamentos` (com `Idempotency-Key`).
4. Responder com o lançamento criado.

### 11.5 Criar serviço terceirizado — "contratei Vitor para gesso dos apt 17 a 20 por 900"
1. `GET /terceirizados/buscar?nome=Vitor` (cadastrar via `POST /terceirizados` se não existir).
2. `GET /cadastros/obras/buscar` → `obraId`; `GET /cadastros/obras/:id/unidades` → `obraUnidadeIds`.
3. Confirmar descrição/valor/obra/unidades/previsão → `POST /terceirizados/servicos` (com `Idempotency-Key`).

## 12. Tratamento de erros

`error` (envelope) para os endpoints novos traz `{ok:false,errorCode,precisaConfirmar,message,candidatos,camposFaltando}`.

| errorCode / HTTP | Significado | O agente deve |
|---|---|---|
| `AMBIGUO` (422) | >1 candidato | perguntar qual (usar `candidatos`) |
| `NAO_ENCONTRADO` (404) | nada bate o nome/id | pedir mais dados |
| `FALTA_CONTA_ORIGEM` (422) | pagamento sem conta | pedir a conta (ex.: "Conta01 CEF?") |
| `FALTA_FORMA_PAGAMENTO` (422) | sem forma | pedir forma (pix/transferência/dinheiro/outro) |
| `DUPLICADO_PROVAVEL` (409) | já existe parecido | confirmar e reenviar `confirmarDuplicado:true` |
| `EXCEDE_VALOR_COMBINADO` (422) | acima do combinado | confirmar extra autorizado + motivo, ou ajustar |
| `SERVICO_FINALIZADO` (422) | serviço fechado | orientar reabrir no web antes |
| `SEM_PERMISSAO` (403) | escopo ausente | informar que a chave não tem o escopo (não tentar de novo) |
| `VALIDACAO` (422) | payload inválido / Zod | corrigir campos (`camposFaltando`) |
| `IDEMPOTENCY_CONFLICT` (409) | mesma chave, payload diferente | usar nova `Idempotency-Key` ou revisar o payload |
| `NAO_IMPLEMENTADO` (501) | operação bloqueada (ex.: fechamento→CP) | orientar usar o sistema web |
| **401** | Bearer ausente/ inválido/ revogado | parar; checar a chave (não logar a chave) |
| **429** | rate limit | aguardar e repetir com backoff |
| **503** | `AGENT_API_ENABLED=false` (kill-switch) | informar indisponibilidade temporária |
| **504** | timeout (>30s) | repetir 1x (POST só com a MESMA Idempotency-Key) |
| **5xx** | erro interno | informar falha; **não** reenviar POST sem mesma Idempotency-Key |

Regra de ouro: **nunca esconder o erro do usuário**; em dúvida, **não gravar**.

## 13. RH, Mão de Obra e Terceirizados

- **Terceirizados/Serviços compõem mão de obra.** Pagamentos reais passam pela **Conta a Pagar oficial**
  (não há tabela paralela) — vinculados por `contas_pagar.servico_terceirizado_id`, com baixa em `PagamentoContaPagar`.
- **Categoria de mão de obra = "Mão de Obra"** (o servidor resolve; bloqueia se não existir — sem fallback).
- **Obra é obrigatória** para mão de obra (CP herda a obra do serviço); **unidade é opcional**.
- Serviço tem **valor combinado, total pago e saldo**; o pagamento respeita saldo/valor combinado (excedente
  exige autorização + motivo).
- **`/rh/resumo` no web** agora soma **Vale + Pagamento + Terceirizados/Serviços = Total Mão de Obra** (o
  endpoint de apoio é `GET /api/rh/servicos-terceirizado/resumo-pagos?mes=` — rota humana, **não** do agente).

## 14. Compatibilidade com o agente atual

- Os **comandos antigos continuam funcionando** (endpoints da seção 5 inalterados; envelope externo inalterado).
- O agente pode continuar **determinístico**: a LLM pode ser **seletor de tools**, **não executor**.
- As novas operações devem virar **tools internas**; comando manual e LLM chamam **a mesma camada de tools**.
- Com a **LLM desligada**, os comandos antigos devem continuar passando normalmente.

## 15. Sugestão de tools internas (no projeto do agente)

**Read (sem confirmação):**

| Tool | Endpoint | Args mínimos | Escopo |
|---|---|---|---|
| `consultar_whoami` | `GET /whoami` | — | (Bearer) |
| `consultar_contas_hoje` | `GET /contas-pagar/hoje` | — | read:financeiro |
| `consultar_contas_vencidas` | `GET /contas-pagar/vencidas` | — | read:financeiro |
| `consultar_contas_proximos_dias` | `GET /contas-pagar/proximos-dias` | `dias` | read:financeiro |
| `consultar_contas_criticas` | `GET /contas-pagar/criticas` | — | read:financeiro |
| `consultar_resumo_diario` | `GET /resumo-diario` | — | read:financeiro |
| `consultar_painel_operacional` | `GET /painel-operacional` | `contaBancariaId?,mes?` | read:financeiro |
| `buscar_funcionarios` | `GET /rh/funcionarios/buscar` | `nome` | read:rh |
| `buscar_fornecedores` | `GET /financeiro/fornecedores/buscar` | `nome` | read:financeiro |
| `buscar_obras` | `GET /cadastros/obras/buscar` | `nome` | read:cadastros |
| `buscar_unidades` | `GET /cadastros/obras/:id/unidades` | `obraId` | read:cadastros |
| `buscar_terceirizados` | `GET /terceirizados/buscar` | `nome` | read:terceirizados |
| `buscar_servicos_terceirizado` | `GET /terceirizados/servicos/buscar` | `nome,status?` | read:terceirizados |
| `detalhar_servico_terceirizado` | `GET /terceirizados/servicos/:id` | `id` | read:terceirizados |
| `buscar_contas_bancarias` | `GET /financeiro/contas-bancarias[/buscar]` | `nome?` | read:financeiro |
| `consultar_fechamento_rh` | `GET /rh/fechamento[/funcionario]` | `mes,tipo[,funcionarioId]` | read:rh |
| `consultar_resumo_rh` / `consultar_extrato_rh` | `GET /rh/resumo` / `/rh/extrato` | `funcionarioId,mes` | read:rh |
| `buscar_pix` / `buscar_extrato` | `GET /extrato/pix/buscar` / `/extrato/buscar` | `valor?,data?,...` | read:extrato |

**Write (SEMPRE com confirmação humana + `Idempotency-Key`):**

| Tool | Endpoint | Args mínimos | Confirmar? | Escopo |
|---|---|---|---|---|
| `criar_conta_pagar` | `POST /financeiro/contas-pagar` (`pago:false`) | fornecedorId,categoriaId,descricao,valor,dataVencimento | **sim** | write:financeiro |
| `criar_conta_pagar_paga` | `POST /financeiro/contas-pagar` (`pago:true`) | +contaBancariaId,formaPagamento,dataPagamento | **sim** | write:financeiro |
| `registrar_pagamento_servico_terceirizado` | `POST /terceirizados/servicos/:id/pagamentos` | valor,dataPagamento,tipo,formaPagamento,contaBancariaId | **sim** | write:terceirizados |
| `criar_lancamento_rh` | `POST /rh/lancamentos` | funcionarioId,tipo,data,qtd,valorUnit | **sim** | write:rh |
| `criar_servico_terceirizado` | `POST /terceirizados/servicos` | funcionarioId,descricao,valorCombinado,obraId | **sim** | write:terceirizados |
| `cadastrar_terceirizado` | `POST /terceirizados` | nome,funcao | **sim** | write:terceirizados ou write:cadastros_basico |

## 16. Checklist de implementação no agente

1. Ler este arquivo. 2. **Não mexer no repositório financeiro.** 3. Atualizar o cliente HTTP (base URL +
Bearer + `Idempotency-Key`). 4. **Preservar os comandos antigos** (seção 5). 5. Criar um **registry de
tools**. 6. Implementar os **GET novos** (seção 6). 7. Implementar camada de **rascunho/confirmação**.
8. Implementar os **POST somente após confirmação**. 9. Implementar **`Idempotency-Key`** (por ação
confirmada). 10. Implementar **tratamento de erros** (seção 12). 11. Testar com **API mock**. 12. Testar
**read-only** em produção. 13. Testar **write primeiro em ambiente local/controlado**, se disponível.
14. **Nunca testar POST em produção sem autorização explícita** (e, se for inevitável, usar marcador de
teste + limpar imediatamente).

## 17. Prompt pronto para o projeto do agente

> Copiar o bloco abaixo no chat/projeto do **Agente Financeiro** (outro Claude Code):

```
Você está no repositório do AGENTE FINANCEIRO (bot Telegram). NÃO está no repositório do sistema
financeiro — não o altere.

Contexto: o sistema financeiro BRGlobal ficou "agent-ready". A especificação completa da API está no
arquivo BRGLOBAL_FINANCEIRO_API_AGENT_READY_2026-06-21.md (copie-o para a raiz deste projeto). Use-o como
fonte da verdade.

Tarefa: adaptar o agente para consumir a nova API sem quebrar o que já existe.

Regras:
- Base: https://lixo.brglobal.com.br/api/agent/v1 ; auth: Authorization: Bearer <BRGLOBAL_API_KEY> (a chave
  vem de variável de ambiente; NUNCA colocar a chave em prompt/log).
- Consumir SOMENTE /api/agent/v1. Nunca banco/Prisma/SQL/rotas humanas JWT.
- Preservar os comandos antigos (/whoami, /hoje, /vencidas, /criticas, /proximos7, /resumo, /painel) — eles
  devem continuar funcionando mesmo com a LLM desligada.
- Implementar as tools de LEITURA (seção 6/15) e, depois, as de ESCRITA (seção 7/15).
- ESCRITA só após CONFIRMAÇÃO HUMANA explícita. Se houver ambiguidade (candidatos) ou faltar
  obra/categoria/conta/forma, PERGUNTAR — nunca forçar gravação.
- Todo POST envia Idempotency-Key (por ação confirmada). Retry de POST só com a MESMA Idempotency-Key.
- A LLM é SELETOR de tools, não executor. Comando manual e LLM chamam a mesma camada de tools.
- Tratar os errorCodes (SEM_PERMISSAO, FALTA_CONTA_ORIGEM, FALTA_FORMA_PAGAMENTO, EXCEDE_VALOR_COMBINADO,
  DUPLICADO_PROVAVEL, SERVICO_FINALIZADO, IDEMPOTENCY_CONFLICT, NAO_IMPLEMENTADO, VALIDACAO) + HTTP 401/403/
  404/429/503/504/5xx — sempre informando o usuário e, em dúvida, NÃO gravando.
- Chave read-only NÃO recebe write. Para escrita, usar uma chave com escopos write (criada de forma
  controlada pelo dono do financeiro).

Entregue: cliente HTTP atualizado, registry de tools (read + write), camada de rascunho/confirmação,
idempotência, tratamento de erros, e testes (mock + read-only em produção). Não teste POST em produção sem
autorização explícita.
```

---

### Apêndice — onde confirmar no código (repositório financeiro)
- Rotas: `apps/api/src/modules/agent/agent.routes.ts` (antigas), `agent-read.routes.ts` (Fase C),
  `agent-write.routes.ts` (Fase D). Escopos: `agent.types.ts`. Middleware/auth/escopo:
  `agent.middleware.ts`. Envelope: hook `preSerialization` em `apps/api/src/app.ts`. Padrão de
  resposta/erro: `agent-response.ts`. Idempotência/auditoria: `agent-idempotency.service.ts` +
  migration `20260620200000_agent_idempotency_audit`. Docs: `docs/api/AGENT_API.md`,
  `docs/checkpoints/CHECKPOINT_AGENT_API_FASE_C_D.md`, `docs/PLANO_AGENT_READY.md`.
- **Qualquer divergência → confiar no código**, não neste resumo.
