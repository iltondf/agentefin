# ADR-0003 — Não usar/depender de "Hermes"

- **Status:** aceito · **Data:** 2026-05-30

## Contexto
"Hermes" era o agente/skill de **WhatsApp** planejado para o financeiro, com
runtime/orquestração/seleção de modelo próprios, construído sobre as rotas
`/api/hermes/*`. Decisão do projeto: **não** reconstruir nem depender desse runtime.

## Decisão
- Construir um **bot de Telegram limpo** consumindo a API de agentes dedicada
  **`/api/agent/v1`** (módulo `agent`, distinto das rotas `hermes`).
- **Não** copiar runtime, orquestração ou seleção de modelo do Hermes.
- Reaproveitar **apenas** documentação útil, endpoints e conceitos de negócio.
- Sem frameworks agênticos (LangChain/CrewAI/AutoGen/n8n/Hermes).

## Consequências
- Código explícito e de baixa abstração; fácil de manter e auditar.
- A API de agentes internamente usa serviços `*-hermes.service.ts` do financeiro —
  isso é detalhe do servidor; o agente depende do **contrato HTTP** `/api/agent/v1`,
  não do runtime Hermes.
