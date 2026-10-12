#!/bin/bash
# Start the LiteLLM proxy + Postgres stack.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

# Ensure env exists (one-time)
if [[ ! -e .env ]]; then
    echo "==> .env not found — creating from .env.example"
    cp .env.example .env
    echo "==> Fill in secrets in .env, then re-run this script."
    exit 1
fi

# docker compose reads .env for interpolation; fall back to sudo if we can't read it
DC="docker compose"
if [[ ! -r .env ]]; then
    echo "==> .env not readable by $(whoami) — using sudo"
    DC="sudo -n docker compose"
fi

$DC up -d
$DC ps
