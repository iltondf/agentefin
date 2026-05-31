#!/usr/bin/env bash
# Deploy/atualização do agentefin na VPS via Docker Compose.
# NÃO expõe porta. Bot Telegram por polling (só saída).
set -euo pipefail

# vai para a raiz do repositório (este script está em scripts/deploy/)
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
echo "==> projeto: $(pwd)"

if [ ! -f .env ]; then
  echo "ERRO: .env não encontrado. Crie-o antes (ver docs/deploy/DEPLOY_DIRETO_VPS_DOCKER.md)." >&2
  exit 1
fi

echo "==> git pull --ff-only"
git pull --ff-only

echo "==> docker compose build"
docker compose build

echo "==> docker compose up -d"
docker compose up -d

echo "==> status"
docker compose ps

echo "==> últimos logs (tail 50)"
docker compose logs --tail=50
