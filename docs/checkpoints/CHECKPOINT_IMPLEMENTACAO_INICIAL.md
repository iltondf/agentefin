# Checkpoint 0001 — Implementação Inicial (MVP leitura)

Data: 2026-05-30.

## Marco
Agente Financeiro (Telegram → BRGlobal `/api/agent/v1`) **implementado, testado,
containerizado e documentado**. Pronto para subir (falta apenas deploy/produção).

## Entregue
- **Código** (`financebot/`): `config`, `logging_setup`, `client` (HTTP robusto),
  `formatters`, `commands` (router), `bot` (middleware), `llm` (opcional), `main`.
- **Comandos:** `/hoje /vencidas /criticas /proximos7 /painel /resumo /whoami /ajuda`.
- **Testes:** 26 passando (unit + integração over-the-wire). Evidência real:
  `/health` 200 e contrato 401 da API de agentes. Ver `operacao/evidencias-testes.md`.
- **Docker:** `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example`.
- **Docs:** estrutura completa em `docs/` (arquitetura, decisões, deploy, operação,
  segurança, roadmap, custos, fluxos, git, troubleshooting).

## Decisões
- Cliente somente leitura (ADR-0001); LLM opcional/off (ADR-0002); não usar Hermes
  (ADR-0003); alvo `/api/agent/v1`.

## Problemas e soluções
- `@prisma/client did not initialize`: gerado via `pnpm run db:generate` (raiz não
  tinha o binário `prisma`). Ver `troubleshooting/prisma-monorepo.md`.
- Discrepância de versão: `bck 16-05` não tem `/api/agent/v1` (404); a base atual
  (28-05) tem (401 sem chave). Contrato confirmado contra a base atual.
- Auditoria final: corrigidos boot com env vazio (`DEFAULT_CONTA_BANCARIA_ID`),
  retry indevido em `404` e fallback de usuário no middleware. 26 testes; Docker OK.

## Problema conhecido / restrição
- Validação **autenticada** (200 com dados reais) pendente: exige API Key (INSERT,
  proibido nesta tarefa). Passo do operador.

## Próximos passos
- Operador: gerar chave + validar `/whoami`; deploy Easypanel.
- Roadmap: resumos automáticos; contas a receber; write com confirmação humana.
