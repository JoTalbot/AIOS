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
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent

DEFAULT_APP_PROFILES = {
    "whatsapp": {
        "title": "WhatsApp", "packages": ["com.whatsapp"],
        "mode": "черновики и подтверждение отправки", "sensitive": False,
    },
    "abank": {
        "title": "A-Bank", "packages": ["ua.com.abank"],
        "mode": "только просмотр и подтверждаемые действия", "sensitive": True,
    },
    "privat24": {
        "title": "Privat24", "packages": ["ua.privatbank.ap24"],
        "mode": "только просмотр и подтверждаемые действия", "sensitive": True,
    },
    "uklon": {
        "title": "Uklon", "packages": ["ua.com.uklontaxi", "ua.com.uklon.uklondriver"],
        "mode": "маршруты и заказы только с подтверждением", "sensitive": True,
    },
    "ime": {
        "title": "iMe Messenger", "packages": ["com.iMe.android"],
        "mode": "черновики и подтверждение отправки", "sensitive": False,
    },
    "easyway": {
        "title": "EasyWay", "packages": [],
        "mode": "маршруты и транспорт после установки приложения", "sensitive": False,
    },
}


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
        self.profiles_path = self.data_dir / "app_profiles.json"
        self.shots_dir = self.data_dir / "screenshots"
        self.dumps_dir = self.data_dir / "ui_dumps"
        self.adb_bin = adb_bin or os.environ.get("AIOS_ADB_BIN") or "/usr/local/bin/aios-adb"

    def config(self) -> dict:
        return _read(self.config_path, {})

    def companion_config(self) -> dict:
        return _read(self.data_dir / "companion.json", {})

    def _companion_request(self, path: str, timeout: int = 12) -> dict:
        cfg = self.companion_config()
        endpoint = str(cfg.get("endpoint") or "").rstrip("/")
        token = str(cfg.get("token") or "")
        if not endpoint or len(token) < 16:
            return {"status": "unconfigured", "error": "Companion ещё не настроен"}
        try:
            request = urllib.request.Request(endpoint + "/" + path.lstrip("/"),
                                             headers={"X-AIOS-Token": token})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            return data if isinstance(data, dict) else {"status": "error", "error": "Некорректный ответ Companion"}
        except urllib.error.HTTPError as exc:
            return {"status": "error", "error": f"Companion HTTP {exc.code}"}
        except Exception as exc:
            return {"status": "offline", "error": str(exc)[:180]}

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
        companion = self._companion_request("health")
        permissions = self._companion_request("permissions")
        report["companion"] = {
            "status": companion.get("status"),
            "connected": companion.get("status") == "ok",
            "permissions": {k: permissions.get(k) for k in ("notification_listener", "accessibility", "location", "camera", "media")}
            if permissions.get("status") == "ok" else {},
        }
        _write(self.health_path, report)
        return report

    def apps(self, limit: int = 100) -> dict:
        if not self.status().get("connected"):
            return {"status": "offline", "apps": []}
        raw = self._shell("pm", "list", "packages", "-3", timeout=45)
        packages = [line.split(":", 1)[-1].strip() for line in raw.splitlines() if ":" in line]
        return {"status": "ok", "count": len(packages), "apps": packages[:limit]}

    def app_profiles(self) -> dict:
        """Определить установленные рабочие приложения и их политику безопасности."""
        app_result = self.apps(limit=2000)
        installed = set(app_result.get("apps") or []) if app_result.get("status") == "ok" else set()
        custom = _read(self.profiles_path, {})
        profiles = []
        for key, base in DEFAULT_APP_PROFILES.items():
            override = custom.get(key) if isinstance(custom.get(key), dict) else {}
            packages = override.get("packages") if isinstance(override.get("packages"), list) else base["packages"]
            found = [package for package in packages if package in installed]
            profiles.append({
                "id": key,
                "title": override.get("title") or base["title"],
                "packages": packages,
                "installed": found,
                "available": bool(found),
                "mode": override.get("mode") or base["mode"],
                "sensitive": bool(override.get("sensitive", base["sensitive"])),
            })
        _write(self.profiles_path, {profile["id"]: profile for profile in profiles})
        return {"status": "ok" if installed else app_result.get("status", "offline"), "profiles": profiles}

    def resolve_package(self, reference: str) -> str | None:
        value = str(reference or "").strip()
        profiles = self.app_profiles().get("profiles") or []
        for profile in profiles:
            if value.casefold() in (str(profile.get("id")).casefold(), str(profile.get("title")).casefold()):
                installed = profile.get("installed") or []
                return installed[0] if installed else None
        return value if "." in value else None

    def open_profile(self, reference: str, confirm: bool = False) -> dict:
        package = self.resolve_package(reference)
        if not package:
            return {"status": "error", "error": "Приложение не найдено или не установлено"}
        return self.open_app(package, confirm=confirm)

    def companion_status(self) -> dict:
        health = self._companion_request("health")
        permissions = self._companion_request("permissions")
        return {"status": health.get("status", "error"), "health": health, "permissions": permissions}

    def notifications(self, limit: int = 20) -> dict:
        data = self._companion_request("notifications")
        notifications = data.get("notifications") if isinstance(data.get("notifications"), list) else []
        return {"status": data.get("status", "error"), "notifications": notifications[-limit:]}

    def accessibility(self) -> dict:
        return self._companion_request("accessibility")

    def ui_snapshot(self, confirm: bool = False) -> dict:
        pending = self._needs_confirm(confirm, "android_ui_snapshot")
        if pending:
            return pending
        return self._companion_request("ui", timeout=20)

    def set_clipboard(self, text: str, confirm: bool = False) -> dict:
        pending = self._needs_confirm(confirm, "android_set_clipboard")
        if pending:
            pending["length"] = len(text or "")
            return pending
        if not text:
            return {"status": "error", "error": "Пустой текст"}
        return self._companion_request("clipboard?" + urllib.parse.urlencode({"text": text}), timeout=20)

    def paste(self, confirm: bool = False) -> dict:
        pending = self._needs_confirm(confirm, "android_paste")
        if pending:
            return pending
        return self.key("KEYCODE_PASTE", confirm=True)

    def tap_ui(self, query: str, confirm: bool = False) -> dict:
        pending = self._needs_confirm(confirm, "android_tap_ui")
        if pending:
            pending["query"] = query
            return pending
        snapshot = self.ui_snapshot(confirm=True)
        if snapshot.get("status") != "ok":
            return snapshot
        needle = str(query or "").casefold()
        for node in snapshot.get("nodes") or []:
            haystack = " ".join(str(node.get(k) or "") for k in ("text", "description", "resource")).casefold()
            bounds = node.get("bounds") or []
            if needle and needle in haystack and len(bounds) == 4:
                x = (int(bounds[0]) + int(bounds[2])) // 2
                y = (int(bounds[1]) + int(bounds[3])) // 2
                result = self.tap(x, y, confirm=True)
                result.update({"matched": True, "x": x, "y": y})
                return result
        return {"status": "error", "error": "UI-элемент не найден"}

    def location(self, confirm: bool = False) -> dict:
        pending = self._needs_confirm(confirm, "android_location")
        if pending:
            return pending
        return self._companion_request("location")

    def files(self, directory: str = "/sdcard/Download", limit: int = 100) -> dict:
        allowed = ("/sdcard/Download", "/sdcard/Documents", "/sdcard/Pictures", "/sdcard/DCIM")
        if not any(directory == root or directory.startswith(root + "/") for root in allowed):
            return {"status": "error", "error": "Разрешены только Download, Documents, Pictures или DCIM"}
        if not self.status().get("connected"):
            return {"status": "offline", "files": []}
        result = self._run(["shell", "ls", "-1", directory], timeout=45)
        if result.returncode != 0:
            return {"status": "error", "error": (result.stderr or result.stdout or "")[:200]}
        entries = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
        return {"status": "ok", "directory": directory, "files": entries[:limit], "count": len(entries)}

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

    def pull_file(self, remote_path: str, confirm: bool = False) -> dict:
        pending = self._needs_confirm(confirm, "android_pull_file")
        if pending:
            pending["path"] = remote_path
            return pending
        allowed = ("/sdcard/Download/", "/sdcard/Documents/", "/sdcard/Pictures/", "/sdcard/DCIM/")
        if not any(remote_path.startswith(root) for root in allowed):
            return {"status": "error", "error": "Файл должен быть в разрешённой папке общего хранилища"}
        if not self.status().get("connected"):
            return {"status": "offline"}
        target_dir = self.data_dir / "files"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / Path(remote_path).name
        pull = self._run(["pull", remote_path, str(target)], timeout=120)
        if pull.returncode != 0 or not target.exists():
            return {"status": "error", "error": (pull.stderr or pull.stdout or "")[:200]}
        target.chmod(0o600)
        return {"status": "ok", "file": str(target), "bytes": target.stat().st_size}

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
