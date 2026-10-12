#!/bin/bash
# Apply all local litellm patches (content-based, line-number independent).
# Run AFTER docker compose pull, before restarting litellm.
#
# Usage:
#   ./apply_patches.sh          # apply all patches
#   ./apply_patches.sh --check  # dry-run: show what would change

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCHES_DIR="$SCRIPT_DIR/patches"

# Work from inside the litellm container
CONTAINER_NAME="${LITELLM_CONTAINER:-litellm}"

echo "==> Applying litellm patches from $PATCHES_DIR"
echo "==> Container: $CONTAINER_NAME"

# Copy script into container and run it
docker cp "$SCRIPT_DIR/apply_patches.py" "$CONTAINER_NAME:/tmp/apply_patches.py"

if [[ "${1:-}" == "--check" ]]; then
    echo "[dry-run mode]"
    docker exec "$CONTAINER_NAME" python3 /tmp/apply_patches.py --check
else
    docker exec "$CONTAINER_NAME" python3 /tmp/apply_patches.py
fi

# Clean up
docker exec "$CONTAINER_NAME" rm -f /tmp/apply_patches.py

echo "==> Done"
