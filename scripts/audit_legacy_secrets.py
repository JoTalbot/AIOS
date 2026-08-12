#!/usr/bin/env python3
"""Report legacy managed-secret locations without printing secret values."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

MANAGED = {
    "AIOS_TELEGRAM_TOKEN",
    "TELEGRAM_BOT_TOKEN",
    "COLAB_LLM_API_KEY",
    "TAILSCALE_AUTH_KEY",
    "TELEGRAM_CHAT_ID",
    "AIOS_OWNER_CHAT_ID",
    "AIOS_AUTO_CODER_CHAT_ID",
}
DEFAULT_PATHS = (
    Path("/root/AIOS/.env"),
    Path("/etc/aios/aios-telegram-bot.env"),
    Path("/etc/aios/aios-auto-coder.env"),
    Path("/root/AIOS/data/.colab_llm.env"),
)


def audit(paths: list[Path]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            key = line.partition("=")[0].strip() if "=" in line else ""
            if key in MANAGED:
                findings.append({"path": str(path), "key": key})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args()
    findings = audit(args.paths or list(DEFAULT_PATHS))
    if args.json:
        print(json.dumps({"legacy_secret_findings": findings}, separators=(",", ":")))
    else:
        print(f"legacy_secret_findings={len(findings)}")
        for finding in findings:
            print(f"legacy_secret_location={finding['path']} key={finding['key']}")
    return 1 if findings and args.fail_on_findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
