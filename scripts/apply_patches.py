#!/usr/bin/env python3
"""
Content-based patcher for litellm local patches.
Uses unique string anchors so it survives upstream reflows/changes.
Run AFTER `docker compose pull`, BEFORE `docker compose restart litellm`.
"""

import sys, os, pathlib

VENV_LITELLM = pathlib.Path(os.environ.get(
    "VENV_LITELLM",
    "/app/.venv/lib/python3.13/site-packages/litellm"
))

# ---------------------------------------------------------------------------
# Each patch: anchor_after  = unique text IMMEDIATELY BEFORE the insertion.
#              new_text      = anchor_after + inserted block.
# If new_text already in file  →  already applied (skip).
# If anchor_after not in file  →  upstream changed; needs review.
# ---------------------------------------------------------------------------

PATCHES = [
    {
        "name": "prometheus.py — add clear_deployment_metrics()",
        "file": VENV_LITELLM / "integrations" / "prometheus.py",
        "anchor_after": (
            "    ):\n"
            "        self.set_litellm_deployment_state(1, litellm_model_name, model_id, api_base, api_provider)\n"
            "\n"
            "    def set_deployment_complete_outage("
        ),
        "new_text": (
            "    ):\n"
            "        self.set_litellm_deployment_state(1, litellm_model_name, model_id, api_base, api_provider)\n"
            "\n"
            "    def clear_deployment_metrics(\n"
            "        self,\n"
            "        model_id: str,\n"
            "        litellm_model_name: str,\n"
            "        api_base: str,\n"
            "        api_provider: str,\n"
            "    ) -> None:\n"
            '        """\n'
            "        Remove litellm_deployment_state gauge series for a given model_id.\n"
            "\n"
            "        Called when a deployment is deleted or replaced so stale series\n"
            "        (e.g. from a reconfigured api_base) do not persist in Prometheus.\n"
            '        """\n'
            "        try:\n"
            "            if not model_id:\n"
            "                return\n"
            "            _labels: Final = prometheus_label_factory(\n"
            "                supported_enum_labels=self.get_labels_for_metric(\n"
            "                    metric_name=\"litellm_deployment_state\"\n"
            "                ),\n"
            "                enum_values=UserAPIKeyLabelValues,\n"
            "                proxy_router=False,\n"
            "            )\n"
            "            _labels.labels.append(\n"
            '                Label(name="litellm_model_name", value=litellm_model_name or "")\n'
            "            )\n"
            "            _labels.labels.append(Label(name=\"model_id\", value=model_id))\n"
            '            _labels.labels.append(Label(name="api_base", value=api_base or ""))\n'
            '            _labels.labels.append(Label(name="api_provider", value=api_provider or ""))\n'
            "            _final_labels = {l.name: l.value for l in _labels.labels}\n"
            "            self.litellm_deployment_state.remove(**_final_labels)\n"
            "        except Exception:\n"
            "            pass\n"
            "\n"
            "    def set_deployment_complete_outage("
        ),
    },
    {
        "name": "router.py — upsert_deployment() clear on replace",
        "file": VENV_LITELLM / "router.py",
        "anchor_after": (
            "                self._unregister_pre_routing_strategy_for_deployment(deployment=_deployment_on_router)\n"
        ),
        "new_text": (
            "                self._unregister_pre_routing_strategy_for_deployment(deployment=_deployment_on_router)\n"
            "                # Clear stale prometheus deployment-state series for the replaced deployment\n"
            "                try:\n"
            "                    from litellm.router_utils.cooldown_callbacks import get_prometheus_logger_from_callbacks\n"
            "                    _pl: Any = get_prometheus_logger_from_callbacks()\n"
            "                    if _pl is not None:\n"
            "                        _pl.clear_deployment_metrics(\n"
            "                            model_id=_deployment_on_router.model_info.id or \"\",\n"
            "                            litellm_model_name=_deployment_on_router.model_name,\n"
            "                            api_base=_deployment_on_router.litellm_params.api_base or \"\",\n"
            "                            api_provider=_deployment_on_router.litellm_params.custom_llm_provider or \"\",\n"
            "                        )\n"
            "                except Exception:\n"
            "                    pass\n"
        ),
    },
    {
        "name": "router.py — delete_deployment() clear on remove",
        "file": VENV_LITELLM / "router.py",
        "anchor_after": (
            '                        "the deployment is out of the model_list and its indices are repaired",\n'
            "                        id,\n"
            "                    )\n"
        ),
        "new_text": (
            '                        "the deployment is out of the model_list and its indices are repaired",\n'
            "                        id,\n"
            "                    )\n"
            "                # Clear stale prometheus deployment-state series for this model_id\n"
            "                try:\n"
            "                    from litellm.router_utils.cooldown_callbacks import get_prometheus_logger_from_callbacks\n"
            "                    _pl: Any = get_prometheus_logger_from_callbacks()\n"
            "                    if _pl is not None:\n"
            "                        _item_model_name = (\n"
            "                            item.model_name\n"
            "                            if isinstance(item, Deployment)\n"
            "                            else item.get(\"model_name\", \"\")\n"
            "                        )\n"
            "                        _item_litellm_params = (\n"
            "                            item.litellm_params\n"
            "                            if isinstance(item, Deployment)\n"
            "                            else item.get(\"litellm_params\", {})\n"
            "                        )\n"
            "                        _pl.clear_deployment_metrics(\n"
            "                            model_id=id,\n"
            "                            litellm_model_name=_item_model_name,\n"
            "                            api_base=_item_litellm_params.api_base or \"\",\n"
            "                            api_provider=_item_litellm_params.custom_llm_provider or \"\",\n"
            "                        )\n"
            "                except Exception:\n"
            "                    pass\n"
        ),
    },
]


def apply_all():
    results = []
    for patch in PATCHES:
        f = patch["file"]
        if not f.exists():
            results.append(f"SKIP  {patch['name']} — file not found: {f}")
            continue

        content = f.read_text()
        anchor = patch["anchor_after"]
        new_text = patch["new_text"]

        if new_text in content:
            results.append(f"OK    {patch['name']} — already applied")
            continue

        if anchor not in content:
            results.append(f"FAIL  {patch['name']} — anchor not found in {f.name}")
            results.append(f"       upstream may have changed this area; manual review needed")
            continue

        content = content.replace(anchor, new_text, 1)
        f.write_text(content)
        results.append(f"PATCH {patch['name']}")

    return results


if __name__ == "__main__":
    dry_run = "--check" in sys.argv

    print(f"litellm path: {VENV_LITELLM}")
    print(f"mode: {'--check (dry-run)' if dry_run else 'apply'}\n")

    for line in apply_all():
        print(line)

    if dry_run:
        print("\n(dry-run — no files written)")
