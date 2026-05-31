#!/usr/bin/env bash
# Status + logs recentes do agentefin na VPS.
set -euo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

docker compose ps
echo "---- logs (tail 100) ----"
docker compose logs --tail=100
