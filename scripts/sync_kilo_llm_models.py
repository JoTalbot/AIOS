#!/usr/bin/env python3
"""Synchronize Kilo's AIOS model catalog from the live LLMBalancer."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

REPO = Path("/root/AIOS")
sys.path.insert(0, str(REPO))

from scripts.llm_balancer_openai_proxy import collect_balancer_catalog

KILO_CONFIG = Path.home() / ".config" / "kilo" / "kilo.jsonc"


def build_kilo_models() -> dict:
    """Convert the proxy catalog to Kilo's OpenAI-compatible model schema."""

    models = {}
    for item in collect_balancer_catalog():
        model_id = item["id"]
        models[model_id] = {
            "id": model_id,
            "name": item["name"],
            "tool_call": True,
            "limit": {
                "context": int(item["context"]),
                "output": int(item["output"]),
            },
        }
    return models


def updated_kilo_config(config: dict, models: dict) -> dict:
    """Return the in-memory config after updating only the AIOS provider."""

    provider = config.setdefault("provider", {}).setdefault("aios", {})
    provider["npm"] = "@ai-sdk/openai-compatible"
    provider["name"] = "AIOS llm_balancer"
    options = provider.setdefault("options", {})
    options["baseURL"] = "http://127.0.0.1:8099/v1"
    options.setdefault("apiKey", "aios-local")
    provider["models"] = models
    if not config.get("model") or config.get("model") == "aios/qwen2.5-coder":
        config["model"] = "aios/auto"
    return config


def sync_kilo_config(path: Path, *, check_only: bool = False) -> tuple[int, bool, str]:
    """Synchronize one config atomically and return model count, changed, default."""

    if not path.exists():
        raise FileNotFoundError(path)
    original = path.read_text(encoding="utf-8")
    config = json.loads(original)
    models = build_kilo_models()
    updated_kilo_config(config, models)
    rendered = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
    changed = rendered != original

    if changed and not check_only:
        mode = stat.S_IMODE(path.stat().st_mode)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            temporary.write_text(rendered, encoding="utf-8")
            os.chmod(temporary, mode)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return len(models), changed, str(config.get("model") or "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=KILO_CONFIG)
    parser.add_argument("--check", action="store_true", help="do not write; exit 1 when synchronization is needed")
    args = parser.parse_args()

    try:
        count, changed, default = sync_kilo_config(args.config, check_only=args.check)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"sync failed: {exc}", file=sys.stderr)
        return 2

    state = "stale" if changed else "current"
    print(f"{state}: {count} models; default={default}; config={args.config}")
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
