"""
AIOS Android Mesh v19.3 — Multi-Device Fleet for Real Phones
Параллельная сеть из N Android-телефонов через WireGuard + ADB.

Одна нода = один телефон (G1, G2...), каждая с serial IP:port, capabilities, battery, heartbeat.
Маршрутизирует задачи на наименее загруженную ноду с нужным приложением.
Совместим с legacy single-device device.json (мигрирует в fleet.json).
"""
from __future__ import annotations

import json
import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone

logger = logging.getLogger("AIOS.AndroidMesh")

DEFAULT_FLEET_FILE = "data/android_gateway/fleet.json"
LEGACY_DEVICE_FILE = "data/android_gateway/device.json"


@dataclass
class MeshDevice:
    serial: str  # 10.203.0.2:46037
    name: str  # G1, G2
    model: str = ""
    android_version: str = ""
    wireguard_ip: str = ""
    status: str = "idle"  # idle, busy, offline, charging
    leased_to: Optional[str] = None
    capabilities: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: float = field(default_factory=time.time)
    battery_pct: Optional[int] = None
    network: str = "wireguard"
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    task_count: int = 0
    error_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def is_online(self) -> bool:
        # offline if no heartbeat >5 min
        return time.time() - self.last_heartbeat < 300 and self.status != "offline"

    @property
    def is_idle(self) -> bool:
        return self.status == "idle" and self.is_online

    def heartbeat(self, battery: Optional[int] = None):
        self.last_heartbeat = time.time()
        if battery is not None:
            self.battery_pct = battery
        if self.status == "offline":
            self.status = "idle"


class AndroidMeshFleet:
    """Fleet manager for N real Android phones."""

    def __init__(self, fleet_file: str | Path | None = None, legacy_file: str | Path | None = None):
        # Resolve data dir (docker/host)
        is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
        base = Path("/app/data") if (is_docker and Path("/app/data").exists()) else Path("data")
        # Allow override
        if fleet_file:
            self.fleet_path = Path(fleet_file)
        else:
            self.fleet_path = Path(fleet_file) if fleet_file else (Path("/root/AIOS") / DEFAULT_FLEET_FILE if Path("/root/AIOS").exists() else base / "android_gateway/fleet.json")
            # Fallback: if running from /root/AIOS, use that
            if not self.fleet_path.exists() and Path("/root/AIOS/data/android_gateway/fleet.json").exists():
                self.fleet_path = Path("/root/AIOS/data/android_gateway/fleet.json")
            elif str(self.fleet_path).startswith("data/") and Path("/root/AIOS").exists():
                # When invoked from /root/AIOS, resolve relative to project
                self.fleet_path = Path("/root/AIOS") / self.fleet_path
        self.legacy_path = Path(legacy_file) if legacy_file else (Path("/root/AIOS") / LEGACY_DEVICE_FILE if Path("/root/AIOS").exists() else base / "android_gateway/device.json")
        if str(self.legacy_path).startswith("data/") and Path("/root/AIOS").exists():
            # resolve
            if not self.legacy_path.is_absolute():
                self.legacy_path = Path("/root/AIOS") / self.legacy_path
        self.devices: Dict[str, MeshDevice] = {}
        self._load()

    def _load(self):
        # Load fleet.json if exists
        if self.fleet_path.exists():
            try:
                data = json.loads(self.fleet_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        try:
                            dev = MeshDevice(**{k: v for k, v in item.items() if k in MeshDevice.__dataclass_fields__})
                            self.devices[dev.serial] = dev
                        except Exception as e:
                            logger.warning(f"Skip device {item.get('serial')}: {e}")
                elif isinstance(data, dict) and "devices" in data:
                    for item in data["devices"]:
                        dev = MeshDevice(**item)
                        self.devices[dev.serial] = dev
            except Exception as e:
                logger.error(f"Fleet load error: {e}")
        # Legacy migration: if fleet empty and device.json exists, migrate
        if not self.devices and self.legacy_path.exists():
            try:
                legacy = json.loads(self.legacy_path.read_text(encoding="utf-8"))
                if legacy.get("serial"):
                    serial = legacy["serial"]
                    dev = MeshDevice(
                        serial=serial,
                        name=legacy.get("name", "G1"),
                        model=legacy.get("model", ""),
                        android_version=str(legacy.get("android", "")),
                        wireguard_ip=serial.split(":")[0] if ":" in serial else "",
                        capabilities=legacy.get("capabilities", {}),
                        status="idle",
                        registered_at=legacy.get("registered_at", datetime.now(timezone.utc).isoformat())
                    )
                    self.devices[serial] = dev
                    logger.info(f"Migrated legacy device {serial} to fleet")
                    self._save()
            except Exception as e:
                logger.error(f"Legacy migration failed: {e}")

    def _save(self):
        try:
            self.fleet_path.parent.mkdir(parents=True, exist_ok=True)
            data = [d.to_dict() for d in self.devices.values()]
            tmp = self.fleet_path.with_name(f".{self.fleet_path.name}.tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.fleet_path)
            try:
                self.fleet_path.chmod(0o600)
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Fleet save error: {e}")

    # --- CRUD ---
    def register_device(self, serial: str, name: str = "", model: str = "", android_version: str = "", capabilities: Dict[str, Any] | None = None) -> MeshDevice:
        if serial in self.devices:
            dev = self.devices[serial]
            if name:
                dev.name = name
            if model:
                dev.model = model
            if android_version:
                dev.android_version = android_version
            if capabilities:
                dev.capabilities = capabilities
            dev.heartbeat()
            self._save()
            return dev
        dev = MeshDevice(
            serial=serial,
            name=name or f"G{len(self.devices)+1}",
            model=model,
            android_version=android_version,
            wireguard_ip=serial.split(":")[0] if ":" in serial else "",
            capabilities=capabilities or {},
        )
        self.devices[serial] = dev
        self._save()
        logger.info(f"Registered mesh device {serial} as {dev.name}")
        return dev

    def remove_device(self, serial: str) -> bool:
        if serial in self.devices:
            del self.devices[serial]
            self._save()
            return True
        return False

    def get_device(self, serial: str) -> Optional[MeshDevice]:
        return self.devices.get(serial)

    def list_devices(self, only_online: bool = False) -> List[MeshDevice]:
        if only_online:
            return [d for d in self.devices.values() if d.is_online]
        return list(self.devices.values())

    # --- Lease / routing ---
    def lease_device(self, task_id: str, require_app: str | None = None, preferred_serial: str | None = None) -> Optional[MeshDevice]:
        """Lease least-loaded idle device that has require_app capability (if specified)."""
        candidates = []
        for dev in self.devices.values():
            if not dev.is_idle:
                continue
            if dev.battery_pct is not None and dev.battery_pct < 15:
                continue  # skip low battery
            if require_app and require_app not in dev.capabilities.get("apps", []) and dev.capabilities:
                # If capabilities has apps list, check; if empty, assume all
                if dev.capabilities.get("apps"):
                    continue
            if preferred_serial and dev.serial != preferred_serial:
                continue
            candidates.append(dev)
        if not candidates:
            # Try any idle ignoring app filter
            candidates = [d for d in self.devices.values() if d.is_idle]
        if not candidates:
            return None
        # Least-loaded: sort by task_count then last_heartbeat
        candidates.sort(key=lambda d: (d.task_count, d.last_heartbeat))
        chosen = candidates[0]
        chosen.status = "busy"
        chosen.leased_to = task_id
        chosen.task_count += 1
        self._save()
        logger.info(f"Leased {chosen.serial} ({chosen.name}) to {task_id} (require_app={require_app})")
        return chosen

    def release_device(self, serial_or_task: str) -> Optional[MeshDevice]:
        for dev in self.devices.values():
            if dev.serial == serial_or_task or dev.leased_to == serial_or_task:
                dev.status = "idle"
                dev.leased_to = None
                dev.heartbeat()
                self._save()
                logger.info(f"Released {dev.serial} ({dev.name})")
                return dev
        return None

    def heartbeat(self, serial: str, battery: Optional[int] = None, status: str | None = None) -> bool:
        dev = self.devices.get(serial)
        if not dev:
            return False
        dev.heartbeat(battery)
        if status:
            dev.status = status
        self._save()
        return True

    def mark_offline(self, serial: str):
        dev = self.devices.get(serial)
        if dev:
            dev.status = "offline"
            self._save()

    def reap_stale(self, stale_sec: int = 600) -> List[str]:
        now = time.time()
        stale = []
        for dev in self.devices.values():
            if dev.status != "offline" and now - dev.last_heartbeat > stale_sec:
                dev.status = "offline"
                stale.append(dev.serial)
        if stale:
            self._save()
            logger.warning(f"Reaped stale devices: {stale}")
        return stale

    # --- Stats & health ---
    def stats(self) -> Dict[str, Any]:
        total = len(self.devices)
        online = len([d for d in self.devices.values() if d.is_online])
        idle = len([d for d in self.devices.values() if d.is_idle])
        busy = len([d for d in self.devices.values() if d.status == "busy"])
        offline = total - online
        return {
            "total": total,
            "online": online,
            "idle": idle,
            "busy": busy,
            "offline": offline,
            "devices": [d.to_dict() for d in self.devices.values()],
            "fleet_file": str(self.fleet_path),
            "legacy_migrated": self.legacy_path.exists()
        }

    def health_report(self) -> Dict[str, Any]:
        report = {"fleet": self.stats(), "checks": []}
        for dev in self.devices.values():
            age = time.time() - dev.last_heartbeat
            report["checks"].append({
                "serial": dev.serial,
                "name": dev.name,
                "online": dev.is_online,
                "idle": dev.is_idle,
                "battery": dev.battery_pct,
                "age_sec": int(age),
                "status": dev.status,
                "leased_to": dev.leased_to
            })
        return report

    def route_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route a phone task to best device. Expects task with 'app' or 'package'."""
        app = task.get("app") or task.get("package") or task.get("require_app")
        task_id = task.get("id") or task.get("task_id") or f"task_{int(time.time())}"
        dev = self.lease_device(task_id, require_app=app)
        if not dev:
            return {"status": "no_device", "error": "No idle mesh device available", "task_id": task_id}
        return {"status": "routed", "task_id": task_id, "device": dev.to_dict(), "app": app}

    def generate_telegram_report(self) -> str:
        s = self.stats()
        lines = ["📱 *AIOS Android Mesh v19.3*", ""]
        lines.append(f"Устройств: `{s['total']}` | Online: `{s['online']}` | Idle: `{s['idle']}` | Busy: `{s['busy']}` | Offline: `{s['offline']}`")
        lines.append("")
        if not s["devices"]:
            lines.append("⚠️ Fleet пуст — зарегистрируйте устройство:")
            lines.append("`python run_android_mesh.py --register 10.203.0.2:46037 --name G1 --model \"Pixel 7\" --android 15`")
            return "\n".join(lines)
        for d in s["devices"]:
            age = int(time.time() - d["last_heartbeat"])
            batt = f"🔋{d['battery_pct']}%" if d["battery_pct"] is not None else ""
            status_emoji = {"idle": "✅", "busy": "⏳", "offline": "❌", "charging": "🔌"}.get(d["status"], "❓")
            lines.append(f"{status_emoji} *{d['name']}* `{d['serial']}` — {d['status']} {batt} age {age}s leased:{d['leased_to'] or '-'} tasks:{d['task_count']}")
        lines.append("")
        if s["idle"] == 0 and s["online"] > 0:
            lines.append("⚠️ Нет idle нод — все заняты. Добавьте устройство.")
        elif s["total"] == 1:
            lines.append("ℹ️ Одна нода — mesh готовность 1/3. Добавьте G2/G3 для параллели.")
        elif s["total"] >= 2 and s["idle"] >= 1:
            lines.append("✅ Mesh готов к параллельным задачам (OLX/банкинг/мессенджеры).")
        lines.append(f"Файл: `{s['fleet_file']}`")
        return "\n".join(lines)
