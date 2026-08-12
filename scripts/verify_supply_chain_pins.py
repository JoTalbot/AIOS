#!/usr/bin/env python3
"""Verify immutable GitHub Action and production image references."""

from __future__ import annotations

import re
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST_IMAGE = re.compile(r"^[^\s:]+(?:/[^\s:]+)*:[^\s@]+@sha256:[0-9a-f]{64}$")


def findings(root: Path) -> list[str]:
    errors: list[str] = []
    workflows = root / ".github" / "workflows"
    for path in workflows.glob("*.y*ml"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = re.search(r"uses:\s*([^\s#]+)@([^\s#]+)", line)
            if match and not match.group(1).startswith("./") and not SHA.fullmatch(match.group(2)):
                errors.append(f"mutable-action:{path.relative_to(root)}:{number}")
    compose = root / "docker-compose.prod.yml"
    for number, line in enumerate(compose.read_text(encoding="utf-8").splitlines(), 1):
        match = re.match(r"\s*image:\s*([^\s#]+)", line)
        if match and not DIGEST_IMAGE.fullmatch(match.group(1)):
            errors.append(f"mutable-image:{compose.relative_to(root)}:{number}")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = findings(root)
    print(f"supply_chain_pin_findings={len(errors)}")
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
