# LiteLLM Proxy — Local Fork

## Upstream

- **Repo:** https://github.com/BerriAI/litellm
- **Image:** `ghcr.io/berriai/litellm:main-latest` (tracks `main` branch)
- **Current version:** `1.106.0.dev3` (in container)

---

## Quick Start

```bash
# Start
docker compose up -d

# Check status
docker compose ps

# Logs
docker compose logs -f litellm

# Stop
docker compose down
```

Environment: see `.env.example` (copy to `.env` and fill in secrets).

Key ports:
| Port | Service |
|------|---------|
| 4000 | LiteLLM proxy (API) |
| 4001 | Prometheus metrics |

---

## Our Patches

### Stale `litellm_deployment_state` Metric Cleanup

**Problem:** Every deployment delete/replace left orphaned series in the
`litellm_deployment_state` Prometheus gauge. After reconfiguration cycles
the metric shows stale model IDs, wrong `api_base` values, and phantom
deployments.

**Fix (2 files):**

1. **`litellm/integrations/prometheus.py`** — adds
   `PrometheusLogger.clear_deployment_metrics()`: removes the gauge series
   for a given `model_id`.

2. **`litellm/router.py`** — calls `clear_deployment_metrics()` in two
   places:
   - `upsert_deployment()` — when a deployment is replaced
   - `delete_deployment()` — when a deployment is removed

**Patch files:** `patches/` directory.

---

## Applying Patches After an Upgrade

Upgrading the image (`docker compose pull` or a new pip install) overwrites
the patched files. Re-apply with:

```bash
# Pull, patch, restart — all in one line
docker compose pull && ./apply_patches.sh && docker compose restart litellm
```

Or step-by-step:

```bash
docker compose pull                 # 1. pull new image
./apply_patches.sh                  # 2. re-apply patches (or --check to preview)
docker compose restart litellm      # 3. restart to load patched code
```

The script is **content-based** — it uses unique text anchors (not line
numbers) so it survives minor upstream reflows.

If a patch anchor shifts or the upstream code changes significantly,
`--check` will report `FAIL` and tell you which patch needs manual review.
In that case, check [GitHub Issue #35654](https://github.com/BerriAI/litellm/issues/35654)
— the fix may already be merged upstream.

### Permanent Fix Options

- **Volume overlay:** mount host-patched files into the container via
  `volumes:` in `docker-compose.yml` so they survive image updates.
- **Custom image:** build your own image on top of `ghcr.io/berriai/litellm`
  with the patches baked in.
- **Upstream fix:** tracked at
  [GitHub Issue #35654](https://github.com/BerriAI/litellm/issues/35654)
  — once merged and released, patches are no longer needed.

---

## File Structure

```
/opt/litellm/
├── .env                     # Secrets (gitignored)
├── .env.example             # Environment template
├── config.yaml              # LiteLLM config (model list, auth, etc.)
├── docker-compose.yml       # Container orchestration
├── .git/                    # Git repo (tracks config + patches only)
├── README.md                # This file
├── apply_patches.py         # Content-based Python patcher
├── apply_patches.sh         # Wrapper script (run this after pull)
└── patches/
    └── 0001-prometheus-...  # Patch file (reference)
```
