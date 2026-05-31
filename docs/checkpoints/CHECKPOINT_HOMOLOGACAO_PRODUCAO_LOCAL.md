# Checkpoint 0002 — Homologação real contra PRODUÇÃO (execução local)

**Data/hora:** 2026-05-31, ~09:18 BRT (12:16–12:18 UTC).

## Marco
Bot validado **ao vivo** consumindo a **API de produção** do BRGlobal com a chave
real do agente, retornando **dados reais**. Bot em execução **local** (ainda não em produção).

## Configuração usada
- **URL:** `https://lixo.brglobal.com.br/api/agent/v1` (produção; TLS ok com AVG desligado).
- **Chave:** `bgf_live_ecffe92489e…` — id 7, "agentefinanceiro", escopos `read:financeiro, read:extrato`.
- **Bot:** `Brglobal_financeiro_bot` (`8431551432:…`), whitelist `ALLOWED_USER_IDS=8646895490`.
- Config em `.env` / `.env.homologacao.local` (ambos **gitignored**).

## Resultados (resumo)
- `GET /health` → 200 `db:ok`.
- **`/whoami` → 200** ✅ (environment=production; prefixo `bgf_live_ecffe92489e`; escopos corretos).
- **`/vencidas` → 7 contas, R$ 19.420,23** (DARF, Prefeitura, DARF Previdenciário, FGTS, Contabilidade, 2× Condor).
- `/resumo` → Vencidas 7 · R$ 19.420,23 · 13 sem código de pagamento.
- `/painel` → Vencidas 7 · R$ 19.420,23 · Conciliação: matches fortes 234, prováveis 75, sugestões pendentes 19.
- `/hoje`, `/criticas`, `/proximos7` → vazios (nada nessas janelas). `/ajuda` → texto local.
- **Dados reais confirmados:** coincidem com o resumo automático das 05:00 do script de cron.

Evidência detalhada: `docs/operacao/evidencias-testes.md` §6.

## Estado
- Bot rodando **LOCALMENTE** (`python -m main`) — **não** em produção.
- O script de cron existente (envia resumo 05:00, sem polling) **convive** com este bot sem conflito.

## Pendências
- **Deploy no Easypanel** (no VPS não há AVG → TLS do Telegram funciona nativamente). Ver `docs/deploy/easypanel.md`.
- ⚠️ **Segurança:** rotacionar `TELEGRAM_BOT_TOKEN` (BotFather `/revoke`) e `BRGLOBAL_API_KEY`
  (`agente:revoke-key` + gerar nova) — ambos apareceram em texto no chat de desenvolvimento.
- Não foi feito: push, deploy, scheduler, novas funcionalidades (fora de escopo nesta etapa).
