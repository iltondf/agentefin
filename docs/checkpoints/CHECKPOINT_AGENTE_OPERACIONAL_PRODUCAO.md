# Checkpoint 0013 — Agente OPERACIONAL em produção (POST real ponta a ponta)

Data: 2026-06-21.

## Marco
O agente financeiro está **operacional em produção** no Telegram, com o ciclo completo
de linguagem natural validado ao vivo, incluindo **um POST real confirmado** e recuperado
exclusivamente pela API agent-ready (sem banco/SQL/Prisma/rotas humanas).

## Ambiente
- **Bot:** `agenteclaudio` (token dedicado; o anterior era compartilhado com um WhatsApp).
- **Deploy:** Docker Compose na VPS (`root@srv822821`, `~/agentefin`), commit `ec19db0`.
- **Flags:** `LLM_ENABLED=true`, `WRITE_ENABLED=true`, `DRAFTS_ENABLED=true`.
- **Modelo LLM:** `deepseek/deepseek-v4-flash` (fallbacks qwen/gemini; vazio → gpt-4o-mini).

## Ciclo validado (guardrail)
mensagem natural → **LLM interpreta** → rascunho → **resumo** → **confirmação humana** →
**POST com Idempotency-Key** → resultado. *Proibido* mensagem natural → POST direto.

## Frases testadas (resumo, sem confirmar) — #13–#18
Datas determinísticas (texto > LLM), conta paga vs pendente, conta 1/2 → 5/6, Pix padrão,
categoria padrão, fornecedor Outros + `[AJUSTAR FORNECEDOR]`, slot-fill de valor faltante.
Pergunta duplicada do slot-fill corrigida (`ec19db0`).

## POST real (ponta a ponta)
- Frase: `[TESTE_AGENT_READY] comprei um item de teste por R$ 1 na Ligar` → `confirmar`.
- **contaPagarId 932** — LIGAR(Walace) 33, "item de teste", R$ 1,00, **pago**, saldo R$ 0,00,
  venc/pag 2026-06-21, categoria 15, obra 4, observações `[AGENT]`, createdAt 18:58:55Z.
- **Sem duplicidade** (idempotência ok). Histórico de escrita do agente: #291 (RH), #929
  (pendente), #930 (paga), **#932** (paga, este teste).
- Recuperado só via `GET /financeiro/contas-pagar/buscar` (filtros + `orderBy=createdAt&order=desc`).
- Rascunhos #13–#18: testes de resumo, **nunca confirmados → nenhum POST**; cancelados no Telegram.

## API agent-ready — busca de CP reescrita (servidor)
`GET /financeiro/contas-pagar/buscar` reescrito em produção (commit servidor `41198e6`, sem
migration): filtros reais (`status, fornecedor, fornecedorId, valor, dataVencimento, dataPagamento,
criadoEmDe/Ate, q, observacao, obraId`), paginação (`page, limit 1–200, hasMore, total`),
ordenação (`orderBy, order`, default `createdAt desc`), validação STRICT (param inválido → 422).
Resultado em `data.data.candidatos`. **Tool `buscar_contas_pagar` do bot atualizado** para usar
esses filtros (default `createdAt desc`; descarta params fora do whitelist).

## Testes
**110 testes** (pytest) verdes. Commits do agente nesta etapa: `6b47445` (datas), `2bf7a50`
(pendente sem vazamento), `ec19db0` (slot-fill sem pergunta duplicada) + esta documentação.

## Pendências / riscos
- 🔒 **Rotacionar chaves expostas no chat** (Telegram token antigo, write key id 17, OpenRouter).
- ⚠️ Alerta web **"Dados de pagamento pendentes"** na #932 — cadastro bancário do fornecedor é
  etapa do sistema web (não bloqueia o registro pelo agente).
- Scheduler/contas a receber: roadmap — **não ativar sem decisão**.
