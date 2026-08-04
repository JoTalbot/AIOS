"""Safe Android app/Companion inventory and drift tracking."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .android_gateway import AndroidGateway

MAX_HISTORY = 90


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read(path: Path, default):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, type(default)) else default
    except Exception:
        return default


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _service_active(name: str) -> bool:
    return subprocess.run(["systemctl", "is-active", "--quiet", name], check=False).returncode == 0


def _age_days(value: object) -> float | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 86400)
    except Exception:
        return None


class PhoneInventory:
    """Tracks only package/profile/capability metadata, never UI or chats."""

    def __init__(
        self,
        root: Path | str,
        gateway_factory: Callable[[Path], AndroidGateway] = AndroidGateway,
        service_probe: Callable[[str], bool] = _service_active,
    ):
        self.root = Path(root)
        self.gateway_factory = gateway_factory
        self.service_probe = service_probe
        self.calibrations_path = self.root / "data" / "android_gateway" / "app_ui_calibrations.json"
        self.path = self.root / "data" / "android_gateway" / "inventory_history.json"

    def _companion_version(self, gateway: AndroidGateway, connected: bool) -> str:
        if not connected:
            return ""
        try:
            raw = gateway._shell("dumpsys", "package", "ua.aios.companion", timeout=15)
            match = re.search(r"versionName=([^\s]+)", raw)
            return match.group(1)[:80] if match else ""
        except Exception:
            return ""

    def snapshot(self) -> dict:
        gateway = self.gateway_factory(self.root)
        device = gateway.status()
        connected = bool(device.get("connected"))
        health = gateway._companion_request("health") if connected else {}
        profiles = gateway.app_profiles().get("profiles") if connected else []
        calibration = _read(self.calibrations_path, {})
        apps = []
        stale = 0
        for profile in profiles or []:
            profile_id = str(profile.get("id") or "")
            cal = calibration.get(profile_id) if isinstance(calibration, dict) else {}
            age = _age_days(cal.get("checked_at")) if isinstance(cal, dict) else None
            if age is not None and age >= 7:
                stale += 1
            apps.append({
                "id": profile_id,
                "available": bool(profile.get("available")),
                "calibrated": bool(isinstance(cal, dict) and cal.get("package")),
                "calibration_age_days": round(age, 1) if age is not None else None,
            })
        return {
            "status": "ok" if connected else "degraded",
            "at": _now(),
            "android": str(device.get("android") or health.get("android") or ""),
            "sdk": int(health.get("sdk") or 0),
            "companion_version": self._companion_version(gateway, connected),
            "wireguard_active": bool(self.service_probe("wg-quick@wg0.service")),
            "apps": apps,
            "apps_available": sum(1 for app in apps if app.get("available")),
            "apps_calibrated": sum(1 for app in apps if app.get("calibrated")),
            "calibrations_stale": stale,
        }

    def record(self) -> dict:
        current = self.snapshot()
        history = _read(self.path, [])
        history = [item for item in history if isinstance(item, dict)]
        previous = history[-1] if history else {}
        previous_apps = {str(app.get("id")): bool(app.get("available")) for app in previous.get("apps", []) if isinstance(app, dict)}
        current_apps = {str(app.get("id")): bool(app.get("available")) for app in current.get("apps", [])}
        drift = sorted(key for key in set(previous_apps) | set(current_apps) if previous_apps.get(key) != current_apps.get(key))
        version_fields = ("android", "sdk", "companion_version", "wireguard_active")
        version_drift = [field for field in version_fields if previous and previous.get(field) != current.get(field)]
        current["availability_drift"] = drift
        current["version_drift"] = version_drift
        history.append(current)
        _write(self.path, history[-MAX_HISTORY:])
        return current

    def latest(self) -> dict:
        rows = _read(self.path, [])
        return rows[-1] if isinstance(rows, list) and rows else {}

    def summary(self) -> dict:
        last = self.latest()
        return {
            "status": "ok", "snapshots": len(self._rows()),
            "availability_drift": list(last.get("availability_drift") or []),
            "version_drift": list(last.get("version_drift") or []),
            "calibrations_stale": int(last.get("calibrations_stale") or 0),
        }
