#!/usr/bin/env python3
"""CLI for private CRM follow-up templates."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from aios_core.followup_templates import FollowupTemplateStore

ROOT = Path(__file__).resolve().parent


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "list"
    store = FollowupTemplateStore(ROOT)
    if command == "list":
        result = {"status": "ok", "templates": store.list()}
    elif command == "summary":
        result = store.summary()
    elif command == "get" and len(sys.argv) >= 3:
        item = store.get(" ".join(sys.argv[2:]))
        result = {"status": "ok", "template": item} if item else {"status": "not_found"}
    elif command == "set" and "|" in sys.argv[2:]:
        divider = sys.argv.index("|")
        result = store.upsert(" ".join(sys.argv[2:divider]), " ".join(sys.argv[divider + 1:]))
    else:
        result = {"status": "error", "error": "list|summary|get <name>|set <name> | <text>"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in ("ok", "created", "updated") else 1


if __name__ == "__main__":
    raise SystemExit(main())
