# Inbox Operacional — design (planejamento, NÃO implementado)

Camada de **captura → rascunho → confirmação humana → gravação via API**. A LLM interpreta;
o agente valida; o humano confirma; a API grava. Nada é lançado por "entendimento" da LLM.

## Modelo de dados da pendência (rascunho)
Campos propostos (tabela `inbox` no BRGlobal, ou rascunho local na transição):
```
id
tipo                 # despesa | compra | rh | pagamento | indefinido
descricao_original   # texto literal que o admin enviou
dados_extraidos:
  valor              # numérico ou null
  data               # ISO ou null
  pessoa_funcionario # nome/id ou null
  fornecedor         # nome/id ou null
  categoria_provavel # sugestão (não definitiva)
  centro_custo_obra  # sugestão ou null
  observacao
  confianca          # 0..1 da interpretação
origem               # "telegram"
usuario_solicitante  # user_id Telegram (auditoria)
status               # pendente_revisao | pendente_confirmacao | confirmado | cancelado | lancado
idempotency_key      # anti-duplicidade
criado_em / atualizado_em
```
**Status nunca pula para `lancado` sem confirmação humana.** `lancado` só após a API gravar.

## Catálogo de tools (por risco — ETAPA 3)
**A) Read-only (já existem):** `consultar_hoje/vencidas/criticas/proximos7/resumo/painel/whoami`.

**B) Captura simples (sem lançamento definitivo) — MVP:**
| Tool | Objetivo | Frase exemplo | Payload mín. | Endpoint | API existe? | Confirma? | Risco | Recom. |
|---|---|---|---|---|---|---|---|---|
| `criar_pendencia_operacional` | guardar pendência textual | "anota p/ revisar depois" | tipo, descricao | `POST /inbox/pendencias` | ❌ criar | sim | baixo | **agora** |
| `listar_pendencias_operacionais` | listar pendências | "o que está pendente?" | filtro status | `GET /inbox/pendencias` | ❌ | não | baixo | agora |
| `consultar_pendencia` | ver 1 pendência | "abre a pendência 12" | id | `GET /inbox/pendencias/:id` | ❌ | não | baixo | agora |
| `cancelar_pendencia` | cancelar | "cancela a 12" | id | `POST /inbox/pendencias/:id/cancelar` | ❌ | sim | baixo | agora |
| `marcar_pendencia_para_revisao` | enviar p/ secretária | "manda p/ revisão" | id | `PATCH status` | ❌ | não | baixo | agora |

**C) RH com rascunho — depois:** `buscar_funcionario` (read), `criar_rascunho_lancamento_funcionario`,
`confirmar_rascunho_funcionario` (grava via `POST /api/rh/lancamentos` por trás), `cancelar_rascunho_funcionario`. Risco médio (ambiguidade de nome, valor/tipo).

**D) Despesa/compra com rascunho — depois:** `buscar_fornecedor`, `criar_rascunho_despesa`,
`criar_rascunho_compra`, `confirmar_rascunho_despesa`, `cancelar_rascunho_despesa`. Risco médio.

**E) Pagamento/conta paga — por último (mais arriscado):** `buscar_conta_pagar`,
`criar_rascunho_pagamento_realizado`, `confirmar_pagamento_realizado` (baixa real via
`POST /api/contas-pagar/:id/baixar`), `cancelar_rascunho_pagamento`. Risco **alto** (baixa indevida).

> Toda tool C/D/E: **rascunho → confirmação humana → grava**. Confirmar é uma ação separada,
> nunca embutida na interpretação.

## Fluxos de conversa (ETAPA 4)
- **Despesa pequena:** interpreta → resume (valor/data/fornecedor/categoria provável) →
  opções: [1] criar pendência [2] lançar despesa [3] corrigir [4] cancelar.
- **RH:** acha funcionário ("Vanderli Souza, confirma?") → tipo/função/data/quantidade →
  pede valor ou regra padrão.
- **Pagamento já feito:** lista contas em aberto do fornecedor → usuário escolhe qual / "criar pendência".
- **Ambiguidade:** ">1 João" → lista numerada → escolher / nenhum.
- **Transversais:** confirmação explícita; correção de campo; cancelamento; múltiplas pendências;
  **expiração** de rascunho não confirmado (ex.: 24h → vira `cancelado`/`pendente_revisao`);
  **anti-duplicidade** via `idempotency_key` (mesmo texto/valor/data/pessoa em janela curta → avisa).

## Validações determinísticas (ETAPA 6 — fora da LLM)
Usuário Telegram autorizado · valor > 0 · data válida · funcionário existe e **ativo** ·
fornecedor existe **ou** fica pendente · categoria permitida **ou** fica pendente · conta
encontrada **ou** fica pendente · tipo ∈ {vale,diária,despesa,compra,pagamento,…} ·
**confirmação explícita** · **idempotency-key** · payload validado por schema · logs sem
segredo · auditoria (origem, usuário, status, timestamps).

## API necessária (ETAPA 7) — recomendação
**Começar pela inbox genérica** (menos superfície, 1 tabela):
```
POST /api/agent/v1/inbox/pendencias            (write:inbox)
GET  /api/agent/v1/inbox/pendencias[/:id]      (read:inbox)
POST /api/agent/v1/inbox/pendencias/:id/cancelar (write:inbox)
# desambiguação (read):
GET  /api/agent/v1/rh/funcionarios?busca=      (read:rh)
GET  /api/agent/v1/fornecedores?busca=         (read:fornecedores)
GET  /api/agent/v1/contas-pagar?busca=         (read:financeiro)
# confirmação que GRAVA — fase posterior:
POST /api/agent/v1/inbox/pendencias/:id/confirmar (confirm:*)
```
Abordagem **A (inbox genérica)** > B (endpoints por domínio) para o MVP. C (só pendência
textual) é o passo mais barato. D (híbrido) é a transição natural.

## Escopos (ETAPA 8) — chave read-only NUNCA escreve
`read:financeiro` · `read:extrato` · `read:rh` · `read:fornecedores` · `write:inbox` ·
`write:rh_rascunho` · `write:despesa_rascunho` · `write:pagamento_rascunho` · `confirm:rh` ·
`confirm:despesa` · `confirm:pagamento`. A chave atual (`read:financeiro,read:extrato`)
**não** ganha escopo de escrita; escrita exige **chave nova** com escopo específico.
