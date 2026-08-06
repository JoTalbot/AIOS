"""Universal real-Android gateway for AIOS.

This module talks to one explicitly paired Android device through ADB over the
private WireGuard network. It treats a phone as a real device node, not an
emulator. Read-only inspection is available immediately; UI-changing actions
require an explicit confirmation flag in the caller.
"""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
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
        "title": "EasyWay", "packages": ["com.eway"],
        "mode": "маршруты и транспорт, без фоновой геолокации", "sensitive": True,
    },
    "olx": {
        "title": "OLX", "packages": ["ua.slando"],
        "mode": "просмотр чатов и черновики с подтверждением", "sensitive": False,
    },
    "viber": {
        "title": "Viber", "packages": ["com.viber.voip"],
        "mode": "чтение уведомлений, просмотр", "sensitive": False,
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
        # app_profiles.json — вычисляемый кэш, а не источник пользовательских
        # настроек. Это важно при обновлении встроенных профилей (например,
        # EasyWay после установки), иначе старый кэш с пустым package-list
        # навсегда переопределял бы новый безопасный default.
        self.profiles_path = self.data_dir / "app_profiles.json"
        self.profile_overrides_path = self.data_dir / "app_profile_overrides.json"
        self.sessions_path = self.data_dir / "control_sessions.json"
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
        # ``None`` means use the registered device; an explicit empty string
        # means a host-wide ADB command such as ``devices`` or ``connect``.
        target = self.serial if serial is None else serial
        command = [self.adb_bin]
        if target:
            command += ["-s", target]
        command += args
        try:
            return subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            # Wireless ADB can leave a launched Android activity alive while
            # the shell process itself does not return.  Convert that into a
            # regular result so callers can verify the foreground package via
            # the authenticated Companion instead of crashing the worker.
            def text(value: object) -> str:
                if isinstance(value, bytes):
                    return value.decode(errors="replace")
                return str(value or "")
            return subprocess.CompletedProcess(
                args=command, returncode=124,
                stdout=text(exc.stdout), stderr=(text(exc.stderr) or "ADB command timed out"),
            )

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
        """Reconnect the paired endpoint, clearing a stale offline ADB entry."""
        endpoint = self.serial
        if not endpoint:
            return {"status": "error", "error": "Телефон ещё не зарегистрирован"}
        listing = self._run(["devices", "-l"], timeout=15, serial="")
        state = ""
        for line in (listing.stdout or "").splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[0] == endpoint:
                state = parts[1]
                break
        if state == "device":
            return {"status": "ok", "message": "ADB уже подключён", "endpoint": endpoint}
        if state in ("offline", "unauthorized", "no"):
            # ``disconnect`` affects only this stale TCP endpoint, never a USB
            # device or the WireGuard tunnel itself.
            self._run(["disconnect", endpoint], timeout=12, serial="")
        result = self._run(["connect", endpoint], timeout=20, serial="")
        return {"status": "ok" if result.returncode == 0 else "error",
                "message": (result.stdout or result.stderr or "").strip()[:300],
                "endpoint": endpoint, "previous_state": state or "absent"}

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
        # Overrides deliberately live outside the generated cache.  Legacy
        # app_profiles.json files are not consumed as overrides: they may hold
        # stale installation state from a previous phone/app version.
        custom = _read(self.profile_overrides_path, {})
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

    @staticmethod
    def _sanitize_ui_snapshot(snapshot: dict, include_text: bool = False) -> dict:
        """Keep accidental screen/chat content out of ordinary diagnostics.

        The Companion only exposes a full node tree after an explicit request.
        This second server-side filter keeps the default CLI/status path safe
        even while an older Companion APK is temporarily installed.
        """
        if not isinstance(snapshot, dict):
            return {"status": "error", "error": "Некорректный UI-ответ"}
        result = {key: value for key, value in snapshot.items() if key != "nodes"}
        nodes = snapshot.get("nodes") if isinstance(snapshot.get("nodes"), list) else []
        cleaned = []
        allowed = ("resource", "class", "clickable", "editable", "bounds")
        for node in nodes[:500]:
            if not isinstance(node, dict):
                continue
            item = {key: node.get(key) for key in allowed if key in node}
            if include_text:
                # Text is intentionally retained only for a directly requested
                # confirmed workflow. Callers must never log this value.
                item["text"] = str(node.get("text") or "")[:1000]
                item["description"] = str(node.get("description") or "")[:1000]
            cleaned.append(item)
        result["nodes"] = cleaned
        return result

    def ui_snapshot(self, confirm: bool = False, include_text: bool = False) -> dict:
        pending = self._needs_confirm(confirm, "android_ui_snapshot")
        if pending:
            return pending
        detail = "full" if include_text else "controls"
        snapshot = self._companion_request("ui?" + urllib.parse.urlencode({"detail": detail}), timeout=20)
        return self._sanitize_ui_snapshot(snapshot, include_text=include_text)

    def active_app_ui(self, package: str, confirm: bool = False, include_text: bool = False) -> dict:
        """Read the active UI only if the Companion proves the foreground app.

        Pasting/clicking based on an unknown foreground window is unsafe: a
        notification, browser or banking screen could otherwise receive text
        intended for a messenger.  New Companion versions provide ``package``
        with each snapshot; older versions are deliberately rejected here.
        """
        snapshot = self.ui_snapshot(confirm=confirm, include_text=include_text)
        if snapshot.get("status") != "ok":
            return snapshot
        active = str(snapshot.get("package") or snapshot.get("package_name") or "").strip()
        if not active:
            return {"status": "error", "error": "Нужна обновлённая версия AIOS Companion для проверки активного приложения"}
        if active != package:
            return {
                "status": "wrong_active_app",
                "expected_package": package,
                "active_package": active,
            }
        return snapshot

    @staticmethod
    def _parse_timestamp(value: object) -> datetime | None:
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None

    def _load_sessions(self) -> dict:
        raw = _read(self.sessions_path, {})
        now = datetime.now(timezone.utc)
        alive: dict[str, dict] = {}
        for session_id, item in raw.items() if isinstance(raw, dict) else []:
            if not isinstance(item, dict):
                continue
            expires = self._parse_timestamp(item.get("expires_at"))
            if expires and expires > now:
                alive[str(session_id)] = item
        if alive != raw:
            _write(self.sessions_path, alive)
        return alive

    def begin_control_session(self, package: str, purpose: str, ttl_seconds: int = 300) -> dict:
        """Create a short-lived, private lease for a confirmed phone workflow."""
        ttl = max(30, min(int(ttl_seconds), 900))
        sessions = self._load_sessions()
        session_id = secrets.token_urlsafe(12)
        now = datetime.now(timezone.utc)
        record = {
            "package": str(package),
            "purpose": str(purpose)[:80],
            "created_at": now.isoformat(timespec="seconds"),
            "expires_at": (now + timedelta(seconds=ttl)).isoformat(timespec="seconds"),
        }
        sessions[session_id] = record
        _write(self.sessions_path, sessions)
        return {"status": "ok", "session_id": session_id, **record}

    def validate_control_session(self, session_id: str, package: str) -> dict:
        record = self._load_sessions().get(str(session_id))
        if not record:
            return {"status": "expired", "error": "Сеанс управления истёк; начните действие заново"}
        if str(record.get("package")) != str(package):
            return {"status": "error", "error": "Сеанс относится к другому приложению"}
        return {"status": "ok", "session_id": str(session_id), **record}

    def end_control_session(self, session_id: str) -> None:
        sessions = self._load_sessions()
        if str(session_id) in sessions:
            sessions.pop(str(session_id), None)
            _write(self.sessions_path, sessions)

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
        # Querying by a visible label is itself an explicit, confirmed action.
        # Keep the full snapshot transient and never expose the matching text
        # in the returned payload.
        snapshot = self.ui_snapshot(confirm=True, include_text=True)
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

    def capture_status(self) -> dict:
        """Return camera/microphone readiness only; never starts capture."""
        return self._companion_request("capture-status")

    def location_status(self) -> dict:
        """Return readiness flags only; this never requests coordinates."""
        return self._companion_request("location-status")

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

    def force_stop(self, package: str) -> dict:
        """Останавливает приложение (для гарантированного холодного старта)."""
        if not self.status().get("connected"):
            return {"status": "offline"}
        result = self._run(["shell", "am", "force-stop", package], timeout=15)
        if result.returncode != 0:
            return {"status": "error", "error": (result.stderr or result.stdout or "")[:200]}
        return {"status": "ok", "package": package}

    def open_app(self, package: str, confirm: bool = False) -> dict:
        pending = self._needs_confirm(confirm, "android_open_app")
        if pending:
            pending["package"] = package
            return pending
        if not self.status().get("connected"):
            return {"status": "offline"}
        # ``monkey -p`` can spend minutes scanning native tombstones even after
        # it has launched the app. Resolve the launcher component and use
        # ActivityManager instead; this has a bounded, deterministic response.
        resolved = self._run(["shell", "cmd", "package", "resolve-activity", "--brief", package], timeout=10)
        candidates = [line.strip() for line in (resolved.stdout or "").splitlines() if "/" in line]
        component = candidates[-1] if resolved.returncode == 0 and candidates else ""
        if component:
            result = self._run(["shell", "am", "start", "-n", component], timeout=15)
        else:
            # Compatibility fallback for unusual launchers. The postcondition
            # below still checks the actual foreground package before success.
            result = self._run(["shell", "monkey", "-p", package, "1"], timeout=12)
        if result.returncode == 0:
            return {"status": "ok", "package": package,
                    "message": (result.stdout or result.stderr or "")[-200:]}
        # Do not retry an opaque input event.  The authenticated Companion is
        # authoritative for this narrow postcondition and prevents duplicate UI
        # interaction after a partial ADB response.
        time.sleep(0.35)
        snapshot = self._companion_request("ui?detail=controls", timeout=6)
        active = str(snapshot.get("package") or snapshot.get("package_name") or "")
        if snapshot.get("status") == "ok" and active == package:
            reason = "таймаута" if result.returncode == 124 else "неполного ответа"
            return {"status": "ok", "package": package,
                    "message": f"Запуск подтверждён через AIOS Companion после {reason} ADB"}
        return {"status": "error", "package": package,
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
