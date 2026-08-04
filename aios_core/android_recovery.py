"""Safe recovery diagnosis for the paired Android transport and Companion."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .android_gateway import AndroidGateway


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


class AndroidRecovery:
    """Diagnose recovery state without screen, location or message access."""

    def __init__(self, root: Path | str, gateway_factory: Callable[[Path], AndroidGateway] = AndroidGateway):
        self.root = Path(root)
        self.gateway_factory = gateway_factory
        self.path = self.root / "data" / "android_gateway" / "recovery.json"

    def check(self) -> dict:
        gateway = self.gateway_factory(self.root)
        registered = bool(gateway.serial)
        reconnect = gateway.connect() if registered else {"status": "unregistered"}
        status = gateway.status() if registered else {"connected": False, "companion": {"connected": False}}
        connected = bool(status.get("connected"))
        companion = bool((status.get("companion") or {}).get("connected"))
        if connected and companion:
            action = "none"
            state = "ok"
        elif not connected and companion:
            action = "wireless_debug_endpoint_needed"
            state = "degraded"
        elif connected and not companion:
            action = "companion_restart_needed"
            state = "degraded"
        else:
            action = "phone_vpn_or_companion_needed"
            state = "degraded"
        report = {
            "status": state,
            "checked_at": _now(),
            "registered": registered,
            "adb_connected": connected,
            "companion_connected": companion,
            "action": action,
            "reconnect_status": str(reconnect.get("status") or ""),
        }
        _write(self.path, report)
        return report
