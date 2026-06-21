# Checkpoint 0008 — Planejamento Agent-Ready (write tools + rascunhos + confirmação)


**Data:** 2026-06-21. **Tipo:** planejamento (sem código/.env/deploy/LLM/POST).

## Contexto
O BRGlobal ficou **agent-ready** (consulta + escrita controlada). Spec copiada para a raiz:
`BRGLOBAL_FINANCEIRO_API_AGENT_READY_2026-06-21.md` (fonte da verdade). Objetivo: evoluir o
agente para "secretária operacional via Telegram" — captura natural → rascunho → confirmação → POST.

## Decisões-chave
- **UM bot** com modos internos (RH, Contas a Pagar, Terceirizados, Consultas, Pendências).
- **LLM = parser** (JSON), nunca executor. Comando manual e LLM → mesma camada de tools.
- **Escrita só após confirmação humana** + `Idempotency-Key` (por ação) + tratamento de erros.
- **Rascunhos em SQLite local** (volume `/app/data` — hoje o compose é stateless → Fase 2 adiciona volume).
- **Duas chaves:** read-only atual (consultas) + **nova com escopos write** (a read-only não recebe write).
- **Defaults** em `defaults.yaml` + overrides SQLite; default usado aparece no resumo.
- Envelope **duplo**: antigos `data`; novos `data.data`/`error` → cliente com 2 unwraps.
- `POST /rh/fechamento/conta-pagar` = **501** (fica no web) → não planejar.

## Tools
- **Read novas** (resolvem IDs): funcionários, fornecedores, obras, unidades, terceirizados,
  serviços, contas bancárias, fechamento/resumo/extrato RH, pix/extrato, contas-pagar/buscar.
- **Write** (confirmação+idem): `criar_lancamento_rh`, `criar_conta_pagar[_paga]`,
  `registrar_pagamento_servico_terceirizado`, `criar_servico_terceirizado`, `cadastrar_terceirizado`.

## Fases
0 doc (esta) · 1 cliente 2-envelopes + read tools · 2 rascunhos SQLite + volume · 3 LLM parser
(sem write) · 4 RH write · 5 financeiro write · 6 terceirizados write · 7 defaults · 8 resumo do
dia · 9 hardening. Escrita só sobe após teste controlado + autorização do 1º POST real.

## Riscos
Escrita indevida (mitigado: confirmação+idempotência) · ambiguidade · perda de rascunho sem
volume · 2 envelopes · rate POST 20/min · chave write · custo LLM · estado mudou entre captura e confirmação.

## Documentos criados
`roadmap/PLANO_AGENT_READY_FASE_WRITE.md` · `arquitetura/AGENT_READY_TOOLS_WRITE_DESIGN.md` ·
`arquitetura/RASCUNHOS_PENDENCIAS_DESIGN.md` · `seguranca/WRITE_CONFIRMATION_GUARDRAILS.md` ·
`seguranca/LLM_PARSER_GUARDRAILS.md` · spec na raiz.

## Estado / restrições
Plano apenas. Agente em produção read-only, intocado. Nada implementado; sem .env/deploy/LLM/POST/
migration; financeiro não alterado (read-only). Substitui/consolida os planos 0006 (LLM tools) e
0007 (secretária operacional) com a API real.

## Próximo passo
Aprovar o plano → Fase 1 (cliente 2-envelopes + registry de tools READ novas, sem escrita),
só após autorização. Escrita exige chave write criada pelo dono do financeiro.
