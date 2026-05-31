# Agente Financeiro (Telegram → BRGlobal Financeiro)

Bot de Telegram **somente leitura** que consulta o **BRGlobal Financeiro** pela
API de agentes (`/api/agent/v1`). Arquitetura simples e explícita:

```
Telegram → Command Router → Finance API Client → BRGlobal API → Resposta
```

**Fonte da verdade:** o BRGlobal Financeiro. O bot **não** acessa o banco direto,
**não** recalcula regra financeira e **não** escreve nada (MVP = leitura).

## Comandos

| Comando | Ação |
|---|---|
| `/hoje` | Contas a pagar que vencem hoje |
| `/vencidas` | Contas vencidas em aberto |
| `/criticas` | Contas críticas (prioridade alta) |
| `/proximos7` | A vencer nos próximos 7 dias |
| `/painel` | Painel operacional consolidado |
| `/resumo` | Resumo diário |
| `/whoami` | Diagnóstico da chave do agente |
| `/ajuda` | Ajuda |

## Rodar local

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # preencha TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS, BRGLOBAL_API_*
python -m main
```

Sem `TELEGRAM_BOT_TOKEN` o processo faz *safe boot* (loga e encerra). Sem
`ALLOWED_USER_IDS` ninguém é autorizado (whitelist vazia = nega todos).

## Testes

```powershell
pip install -r requirements-dev.txt
python -m pytest -q
```

## Configuração (ENV)

Ver [`.env.example`](.env.example). Principais: `TELEGRAM_BOT_TOKEN`,
`ALLOWED_USER_IDS`, `BRGLOBAL_API_BASE_URL`, `BRGLOBAL_API_KEY`. LLM é **opcional
e desligada por padrão** (`LLM_ENABLED=false`) — o bot funciona 100% sem LLM.

## Documentação

- [`docs/ESTADO-ATUAL.md`](docs/ESTADO-ATUAL.md) — ponto de entrada / handoff
- [`docs/arquitetura/`](docs/arquitetura) — decisão inicial + mapa da API
- [`docs/deploy/DEPLOY_DIRETO_VPS_DOCKER.md`](docs/deploy/DEPLOY_DIRETO_VPS_DOCKER.md) — deploy (VPS Docker Compose)
- [`docs/operacao/runbook.md`](docs/operacao/runbook.md) — operação
- [`docs/changelog.md`](docs/changelog.md) · [`docs/checkpoints/`](docs/checkpoints)

## Deploy

**Docker Compose direto na VPS** (sem Easypanel, sem porta — bot por polling, só
conexões de saída). Guia: [`docs/deploy/DEPLOY_DIRETO_VPS_DOCKER.md`](docs/deploy/DEPLOY_DIRETO_VPS_DOCKER.md).
```bash
git clone https://github.com/iltondf/agentefin.git && cd agentefin
# criar .env (ver guia), então:
bash scripts/deploy/vps-docker-deploy.sh
```
