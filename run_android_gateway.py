#!/usr/bin/env python3
"""CLI для универсального Android Device Adapter AIOS."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from aios_core.android_gateway import AndroidGateway

ROOT = Path(__file__).resolve().parent


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    gateway = AndroidGateway(ROOT)
    if command == "register" and len(sys.argv) >= 3:
        result = gateway.register(sys.argv[2], " ".join(sys.argv[3:]) or "Android phone")
    elif command == "connect":
        result = gateway.connect()
    elif command == "status":
        result = gateway.status()
    elif command == "apps":
        result = gateway.apps()
    elif command == "profiles":
        result = gateway.app_profiles()
    elif command == "companion":
        result = gateway.companion_status()
    elif command == "notifications":
        result = gateway.notifications()
    elif command == "accessibility":
        result = gateway.accessibility()
    elif command == "ui-snapshot":
        result = gateway.ui_snapshot(confirm="--confirm" in sys.argv)
    elif command == "clipboard" and len(sys.argv) >= 3:
        result = gateway.set_clipboard(" ".join(sys.argv[2:]).replace(" --confirm", ""), confirm="--confirm" in sys.argv)
    elif command == "paste":
        result = gateway.paste(confirm="--confirm" in sys.argv)
    elif command == "tap-ui" and len(sys.argv) >= 3:
        result = gateway.tap_ui(" ".join(sys.argv[2:]).replace(" --confirm", ""), confirm="--confirm" in sys.argv)
    elif command == "location":
        result = gateway.location(confirm="--confirm" in sys.argv)
    elif command == "files":
        result = gateway.files(sys.argv[2] if len(sys.argv) > 2 else "/sdcard/Download")
    elif command == "pull" and len(sys.argv) >= 3:
        result = gateway.pull_file(sys.argv[2], confirm="--confirm" in sys.argv)
    elif command == "screenshot":
        result = gateway.screenshot()
    elif command == "ui-dump":
        result = gateway.ui_dump()
    elif command == "open" and len(sys.argv) >= 3:
        result = gateway.open_profile(sys.argv[2], confirm="--confirm" in sys.argv)
    elif command == "tap" and len(sys.argv) >= 4:
        result = gateway.tap(int(sys.argv[2]), int(sys.argv[3]), confirm="--confirm" in sys.argv)
    elif command == "home":
        result = gateway.key("KEYCODE_HOME", confirm="--confirm" in sys.argv)
    elif command == "back":
        result = gateway.key("KEYCODE_BACK", confirm="--confirm" in sys.argv)
    elif command == "watch":
        interval = 30
        if "--interval" in sys.argv:
            index = sys.argv.index("--interval")
            if index + 1 < len(sys.argv):
                interval = max(10, int(sys.argv[index + 1]))
        while True:
            result = gateway.connect()
            result["health"] = gateway.status()
            print(json.dumps(result, ensure_ascii=False), flush=True)
            time.sleep(interval)
    else:
        result = {"status": "error", "error": "register|connect|status|apps|profiles|companion|notifications|accessibility|ui-snapshot|clipboard|paste|tap-ui|location|files|pull|screenshot|ui-dump|open|tap|home|back|watch"}
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("status") in ("ok", "offline", "unregistered", "need_confirm") else 1


if __name__ == "__main__":
    raise SystemExit(main())
