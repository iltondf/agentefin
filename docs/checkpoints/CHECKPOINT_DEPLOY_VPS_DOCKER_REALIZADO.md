# Checkpoint 0005 — Deploy real na VPS (Docker Compose) REALIZADO

**Data/hora:** 2026-05-31, ~18:41 BRT.

## Contexto
O agente financeiro (MVP somente leitura, comandos Telegram) foi **publicado em
produção na VPS** via Docker Compose e validado ao vivo no Telegram com dados reais.

## Motivo da mudança (Easypanel → Docker Compose na VPS)
Easypanel gratuito limitado a **3 projetos** (já em uso). Optou-se por **Docker
Compose direto na VPS**: mais simples e suficiente (bot por polling, sem tráfego de entrada).

## Ambiente
- **VPS:** `root@srv822821` (Hostinger). Projeto: `~/agentefin`.
- Docker 28.4 · Docker Compose v2.39 · git 2.34.
- **Commit implantado:** `9ca3e3e` (origin/main).

## Arquitetura final
```
VPS → Docker Compose → container `agentefin` (python -m main)
     → Telegram (polling, brglobalcontas_bot)
     → BRGlobal API (https://lixo.brglobal.com.br/api/agent/v1)
```
Sem porta, sem domínio, sem proxy, sem SSL. Stateless (sem volumes; logs em stdout).

## Arquivos principais
- `Dockerfile`, `docker-compose.yml` (serviço/container `agentefin`, `restart: unless-stopped`, sem ports/volumes, rotação de logs).
- `scripts/ops/agentefin-vps.sh` (operador/menu) · `scripts/deploy/vps-docker-{deploy,status,stop}.sh`.
- Docs: `deploy/DEPLOY_DIRETO_VPS_DOCKER.md`, `deploy/OPERADOR_VPS_INTERATIVO.md`.

## Variáveis usadas (sem valores secretos)
`TELEGRAM_BOT_TOKEN` (segredo) · `ALLOWED_USER_IDS=8646895490` ·
`BRGLOBAL_API_BASE_URL=https://lixo.brglobal.com.br/api/agent/v1` ·
`BRGLOBAL_API_KEY` (segredo, `bgf_live_`) · `TZ=America/Sao_Paulo` · `LLM_ENABLED=false` ·
(opcionais/futuras: `LLM_PROVIDER`, `LLM_MODEL`, `OPENROUTER_API_KEY`, `HTTP_*`, `RATE_LIMIT_PER_MIN`, `LOG_LEVEL`).

## Evidências de funcionamento
- Container `agentefin` **`Up`** (`COMMAND "python -m main"`, sem portas).
- Bot responde no Telegram (polling ativo) — `bot_start` contra a API de produção.
- `/start` (ajuda) e `/painel` confirmados ao vivo; `/painel` = Vencidas 7 · R$ 19.420,23 ·
  Próx. 7 dias 1 · R$ 529,04 · Conciliação 234/75 · sugestões 19 (dados reais).
- Detalhes: `docs/operacao/evidencias-testes.md` §7 (e §6 da homologação).

## Comandos testados
`/start`(=/ajuda) e `/painel` ao vivo na VPS; demais (`/whoami /hoje /vencidas
/criticas /proximos7 /resumo`) validados na homologação com a mesma API/chave de produção.

## Estado atual
**EM PRODUÇÃO NA VPS.** Bot local **parado**. LLM **desativada**. Scheduler **inexistente**.
Fase: **MVP leitura por comandos**.

## Pendências futuras
- **Opcional futuro:** avaliar rotação/revogação da chave antiga por higiene de segurança.
- (Opcional) Apagar o bot antigo `Brglobal_financeiro_bot` no BotFather.
- Fase 2 (resumos automáticos / contas a receber / write com confirmação) — **só após decisão**.

## Como atualizar
`git push` no PC → SSH na VPS → `bash scripts/ops/agentefin-vps.sh` → opção **3**.

## Como operar
`bash scripts/ops/agentefin-vps.sh` (configurar `.env`, status, logs, restart, parar,
validar `/whoami`). Ver `docs/deploy/OPERADOR_VPS_INTERATIVO.md`.
