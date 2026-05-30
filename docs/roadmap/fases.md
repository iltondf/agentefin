# Roadmap por fases

## Fase 1 — MVP leitura ✅ (esta entrega)
Comandos read-only via `/api/agent/v1`: `/hoje /vencidas /criticas /proximos7
/painel /resumo /whoami /ajuda`. Determinístico, sem LLM no caminho crítico.

## Fase 2 — Resumos automáticos (proativo)
Scheduler "burro" (asyncio) dispara resumo diário (manhã/tarde) e alertas de
vencidas/críticas via broadcast aos autorizados. Dedupe em SQLite local (`fin_*`).
Gated por env (`SECRETARY_MODE`). **Não** recalcula nada — usa `resumo-diario`/
`painel-operacional`.

## Fase 3 — Consultas avançadas
Contas a **receber**, caixa do mês, tendências/anomalias, busca por fornecedor.
**Dependência externa:** o BRGlobal precisa expor sob `/api/agent/v1` o que hoje
está só em rotas humanas (`contas-receber`, `contexto-agente`, `financeiro-inteligencia`).

## Fase 4 — Operações com confirmação humana (write)
Agente **propõe** (solicitar baixa / marcar despesa paga); humano confirma no app.
Exige: endpoints de escrita no BRGlobal (hoje só os escopos `write:*` existem),
`Idempotency-Key`, fluxo de dupla confirmação no Telegram. **Nunca** pagamento
automático real.

## Itens que só entram quando "doerem" (não antecipar)
LLM ligada por padrão; persistência além de dedupe; múltiplas contas bancárias como
dimensão de config; réplicas/escala.
