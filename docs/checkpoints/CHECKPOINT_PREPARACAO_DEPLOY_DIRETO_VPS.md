# Checkpoint 0003 — Preparação de deploy direto na VPS (Docker Compose)

**Data:** 2026-05-31.

## Decisão
- **Easypanel descartado** para este agente: a licença gratuita limita a **3 projetos**
  (já em uso). Optou-se por **Docker Compose direto na VPS**.
- Bot Telegram por **polling** → **sem porta, sem domínio, sem proxy, sem SSL**.
- Mantido o escopo: **sem scheduler, sem Fase 2, sem novas funcionalidades.**

## O que foi preparado (sem deploy real)
- `docker-compose.yml` ajustado: serviço/container **`agentefin`**, `restart: unless-stopped`,
  `env_file: .env`, **sem `ports`**, **sem `volumes`** (stateless; logs em stdout),
  rotação de logs (json-file 10MB×3).
- `docs/deploy/DEPLOY_DIRETO_VPS_DOCKER.md` (10 passos: clonar, `.env`, subir, logs,
  reiniciar, atualizar, parar, validar).
- Scripts: `scripts/deploy/vps-docker-deploy.sh`, `…/vps-docker-status.sh`, `…/vps-docker-stop.sh`.
- `.gitattributes` força **LF** em `*.sh` (evita shebang quebrado na VPS Linux).
- Easypanel doc marcado como **descontinuado** (aponta para o novo guia).

## Estado
- Bot local **parado** (0 instâncias `python -m main`); nenhuma API local no ar.
- Código no GitHub (`origin/main`, push já feito). **Sem deploy real ainda.**

## Pendências
1. **Rotacionar** `TELEGRAM_BOT_TOKEN` (BotFather) e gerar **nova** `BRGLOBAL_API_KEY` (não expor).
2. **Criar `.env` na VPS** (com as credenciais novas).
3. **Subir o container** (`scripts/deploy/vps-docker-deploy.sh`).
4. **Testar no Telegram** os 8 comandos.
5. **Opcional futuro:** avaliar rotação/revogação da chave antiga por higiene de segurança.
