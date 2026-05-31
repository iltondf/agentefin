# Checkpoint 0006 — Planejamento da Fase 2 (LLM como seletor de tools)

**Data:** 2026-05-31. **Tipo:** planejamento (sem código, sem deploy, sem ativar LLM).

## Decisão
Na Fase 2, a LLM entra **apenas** como **seletor de tools read-only + redator**:
interpreta a mensagem → escolhe **uma** tool permitida → passa args simples → recebe os
dados da API → redige resposta curta. **Não** acessa banco/Prisma/SQL/HTTP livre, **não**
executa, **não** escreve, **não** calcula valor definitivo. API BRGlobal = fonte da verdade.

## Como os comandos viram tools
`/whoami /hoje /vencidas /criticas /proximos7 /resumo /painel` passam a ser **tools internas**
(`consultar_*`) com `run()` (chama o endpoint fixo) e `format()` (redação determinística).
Comando e LLM despacham para a **mesma** tool. Tools compostas futuras: `gerar_resumo_executivo`,
`explicar_painel`, `gerar_checklist_prioridades`.

## Arquitetura (resumo)
`Telegram → router determinístico (comando/padrão → tool, 0 token) → senão, se LLM_ENABLED:
LLM#1 escolhe tool (whitelist) → agente executa tool (API, Bearer no agente) → LLM#2 redige
do payload → Telegram`. Falha de LLM → fallback determinístico/ajuda; nunca derruba o bot.
`LLM_ENABLED=false` mantém o comportamento atual.

## Guardrails (obrigatórios)
Ver `docs/seguranca/LLM_GUARDRAILS.md`: LLM nunca toca banco/segredo/execução/escrita/cálculo;
args validados (clamp); anti-injection; payload resumido; logs sem segredo; fonte = API.

## Plano por fases
2.0 doc (esta) · 2.1 registry de tools (refactor, sem LLM) · 2.2 LLM seletor p/ pergunta livre
· 2.3 tools compostas · 2.4 contexto curto. Critérios de aceite em `PLANO_LLM_FASE_2.md` §8.

## Documentos criados
- `docs/roadmap/PLANO_LLM_FASE_2.md`
- `docs/arquitetura/LLM_TOOLS_DESIGN.md`
- `docs/seguranca/LLM_GUARDRAILS.md`

## Estado
Agente **em produção** no MVP determinístico (sem LLM). Fase 2 **apenas planejada** — nada
implementado, `.env`/container/BRGlobal intocados, scheduler inexistente.

## Próximo passo
Aprovar o plano → iniciar **Fase 2.1** (registry de tools interno, refactor seguro, sem LLM),
só após autorização explícita.
