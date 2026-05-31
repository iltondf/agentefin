#!/usr/bin/env bash
# Para o agentefin na VPS (derruba o container).
set -euo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

docker compose down
echo "agentefin parado."
