#!/bin/bash
# Stop the LiteLLM proxy + Postgres stack (keeps volumes).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

DC="docker compose"
if [[ ! -r .env ]]; then
    echo "==> .env not readable by $(whoami) — using sudo"
    DC="sudo -n docker compose"
fi

$DC down
