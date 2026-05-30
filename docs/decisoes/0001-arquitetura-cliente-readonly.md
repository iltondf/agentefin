# ADR-0001 — Cliente conversacional somente leitura

- **Status:** aceito · **Data:** 2026-05-30

## Contexto
O BRGlobal Financeiro já implementa toda a regra de negócio (OFX/Pix, conciliação,
baixa, scoring de criticidade, fechamento de caixa) e expõe uma API de agentes
read-only (`/api/agent/v1`).

## Decisão
O agente é um **cliente conversacional somente leitura** dessa API. Ele **não**
acessa o banco direto, **não** recalcula regra financeira e **não** escreve (MVP).
Arquitetura: `Telegram → Command Router → Finance API Client → BRGlobal API`.

## Consequências
- Domínio do agente fica fino (cliente + formatação). Servidor é a fonte da verdade.
- Sem risco de inconsistência (não duplica cálculo).
- Escrita (baixa/solicitação) fica para fase futura, com confirmação humana e
  endpoints de escrita do servidor (que ainda não existem).
