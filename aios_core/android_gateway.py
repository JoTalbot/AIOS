"""Universal real-Android gateway for AIOS.

This module talks to one explicitly paired Android device through ADB over the
private WireGuard network. It treats a phone as a real device node, not an
emulator. Read-only inspection is available immediately; UI-changing actions
require an explicit confirmation flag in the caller.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read(path: Path, default: Any) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, type(default)) else default
    except Exception:
        return default


def _write(path: Path, value: Any, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    try:
        path.chmod(mode)
    except OSError:
        pass


class AndroidGateway:
    """Safe ADB gateway for the paired personal Android phone."""

    def __init__(self, root: Path | str | None = None, adb_bin: str | None = None):
        self.root = Path(root) if root is not None else PROJECT_ROOT
        self.data_dir = self.root / "data" / "android_gateway"
        self.config_path = self.data_dir / "device.json"
        self.health_path = self.data_dir / "health.json"
        self.shots_dir = self.data_dir / "screenshots"
        self.dumps_dir = self.data_dir / "ui_dumps"
        self.adb_bin = adb_bin or os.environ.get("AIOS_ADB_BIN") or "/usr/local/bin/aios-adb"

    def config(self) -> dict:
        return _read(self.config_path, {})

    @property
    def serial(self) -> str:
        return str(self.config().get("serial") or "")

    def _run(self, args: list[str], timeout: int = 30, serial: str | None = None) -> subprocess.CompletedProcess:
        target = serial or self.serial
        command = [self.adb_bin]
        if target:
            command += ["-s", target]
        command += args
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout)

    def _shell(self, *args: str, timeout: int = 30) -> str:
        result = self._run(["shell", *args], timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "adb shell error")[:300])
        return (result.stdout or "").replace("\r", "").strip()

    def register(self, endpoint: str, name: str = "Android phone") -> dict:
        """Register an already paired and connected ADB endpoint."""
        endpoint = str(endpoint or "").strip()
        if not endpoint or ":" not in endpoint:
            return {"status": "error", "error": "Нужен endpoint вида 10.x.x.x:порт"}
        result = self._run(["devices", "-l"], timeout=15, serial="")
        lines = (result.stdout or "").splitlines()[1:]
        connected = any(len(parts := line.split()) >= 2 and parts[0] == endpoint and parts[1] == "device"
                        for line in lines)
        if not connected:
            return {"status": "error", "error": "ADB endpoint не подключён"}
        def read_prop(prop: str) -> str:
            prop_result = self._run(["shell", "getprop", prop], timeout=15, serial=endpoint)
            if prop_result.returncode != 0:
                return ""
            return (prop_result.stdout or "").replace("\r", "").strip()

        model = read_prop("ro.product.model")
        android = read_prop("ro.build.version.release")
        cfg = {
            "name": name[:80] or "Android phone",
            "serial": endpoint,
            "model": model,
            "android": android,
            "registered_at": _now(),
            "safe_mode": True,
            "capabilities": {
                "ui_automation": True,
                "screenshots": True,
                "app_inventory": True,
                "file_transfer": True,
                "notifications": "requires explicit permission/compatible Android build",
                "sms_calls_camera": "requires companion app or explicit user action",
                "payments_biometrics": "manual confirmation only",
            },
        }
        _write(self.config_path, cfg)
        try:
            self.data_dir.chmod(0o700)
        except OSError:
            pass
        return {"status": "ok", "device": cfg}

    def connect(self) -> dict:
        endpoint = self.serial
        if not endpoint:
            return {"status": "error", "error": "Телефон ещё не зарегистрирован"}
        result = self._run(["connect", endpoint], timeout=20, serial="")
        return {"status": "ok" if result.returncode == 0 else "error",
                "message": (result.stdout or result.stderr or "").strip()[:300]}

    def status(self) -> dict:
        cfg = self.config()
        if not cfg.get("serial"):
            return {"status": "unregistered", "connected": False}
        result = self._run(["get-state"], timeout=15)
        connected = result.returncode == 0 and (result.stdout or "").strip() == "device"
        report = {
            "status": "ok" if connected else "offline",
            "connected": connected,
            "serial": cfg.get("serial"),
            "name": cfg.get("name"),
            "model": cfg.get("model"),
            "android": cfg.get("android"),
            "checked_at": _now(),
        }
        if connected:
            try:
                battery = self._shell("dumpsys", "battery")
                for line in battery.splitlines():
                    if line.strip().startswith("level:"):
                        report["battery"] = int(line.split(":", 1)[1].strip())
                        break
                report["screen"] = self._shell("wm", "size")
                report["packages"] = len(self._shell("pm", "list", "packages").splitlines())
            except Exception as exc:
                report["warning"] = str(exc)[:180]
        _write(self.health_path, report)
        return report

    def apps(self, limit: int = 100) -> dict:
        if not self.status().get("connected"):
            return {"status": "offline", "apps": []}
        raw = self._shell("pm", "list", "packages", "-3", timeout=45)
        packages = [line.split(":", 1)[-1].strip() for line in raw.splitlines() if ":" in line]
        return {"status": "ok", "count": len(packages), "apps": packages[:limit]}

    def screenshot(self) -> dict:
        if not self.status().get("connected"):
            return {"status": "offline"}
        self.shots_dir.mkdir(parents=True, exist_ok=True)
        path = self.shots_dir / f"android_{int(time.time())}.png"
        command = [self.adb_bin, "-s", self.serial, "exec-out", "screencap", "-p"]
        with path.open("wb") as file:
            result = subprocess.run(command, stdout=file, stderr=subprocess.PIPE, timeout=45)
        if result.returncode != 0 or not path.exists() or path.stat().st_size < 100:
            path.unlink(missing_ok=True)
            return {"status": "error", "error": (result.stderr or b"screencap error").decode(errors="ignore")[:200]}
        path.chmod(0o600)
        return {"status": "ok", "file": str(path), "bytes": path.stat().st_size}

    def ui_dump(self) -> dict:
        if not self.status().get("connected"):
            return {"status": "offline"}
        self.dumps_dir.mkdir(parents=True, exist_ok=True)
        remote = "/sdcard/window.xml"
        result = self._run(["shell", "uiautomator", "dump", remote], timeout=30)
        if result.returncode != 0:
            return {"status": "error", "error": (result.stderr or result.stdout or "")[:200]}
        path = self.dumps_dir / f"ui_{int(time.time())}.xml"
        pull = self._run(["pull", remote, str(path)], timeout=30)
        if pull.returncode != 0:
            return {"status": "error", "error": (pull.stderr or pull.stdout or "")[:200]}
        path.chmod(0o600)
        return {"status": "ok", "file": str(path)}

    @staticmethod
    def _needs_confirm(confirm: bool, action: str) -> dict | None:
        if not confirm:
            return {"status": "need_confirm", "action": action}
        return None

    def open_app(self, package: str, confirm: bool = False) -> dict:
        pending = self._needs_confirm(confirm, "android_open_app")
        if pending:
            pending["package"] = package
            return pending
        if not self.status().get("connected"):
            return {"status": "offline"}
        result = self._run(["shell", "monkey", "-p", package, "1"], timeout=30)
        return {"status": "ok" if result.returncode == 0 else "error", "package": package,
                "message": (result.stdout or result.stderr or "")[-200:]}

    def tap(self, x: int, y: int, confirm: bool = False) -> dict:
        pending = self._needs_confirm(confirm, "android_tap")
        if pending:
            pending.update({"x": x, "y": y})
            return pending
        result = self._run(["shell", "input", "tap", str(int(x)), str(int(y))], timeout=20)
        return {"status": "ok" if result.returncode == 0 else "error"}

    def key(self, keycode: str, confirm: bool = False) -> dict:
        pending = self._needs_confirm(confirm, "android_key")
        if pending:
            pending["keycode"] = keycode
            return pending
        result = self._run(["shell", "input", "keyevent", keycode], timeout=20)
        return {"status": "ok" if result.returncode == 0 else "error"}
