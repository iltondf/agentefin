# ADR-0002 — LLM opcional, desligada por padrão

- **Status:** aceito · **Data:** 2026-05-30

## Contexto
Comandos financeiros são determinísticos: comando → endpoint → formatação. A LLM
agrega valor só em texto livre, e tem custo/latência/risco.

## Decisão
`LLM_ENABLED=false` por padrão. O agente funciona **100% sem LLM**: todos os
comandos resolvem em Python puro (0 token). Quando habilitada por env, a LLM apenas
**redige** resposta a texto livre, sobre dados já obtidos da API — nunca está no
caminho crítico de um comando, nunca acessa API/banco direto. Anti-injection: dados
vão num bloco delimitado com instrução fixa.

## Consequências
- Confiabilidade e custo previsíveis; degradação trivial (LLM off = usa comandos).
- Sem "seleção de modelo" complexa (decisão aprovada: não copiar isso do Hermes).
