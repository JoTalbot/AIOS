"""AIOS Android Device Fleet (M4).

Device pool: lease/release/heartbeat/sticky route across emulators/devices.
Each profile can be bound to a dedicated device serial for parallel automation.
Auto-restarts stuck emulators and exposes basic balancing.
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

__all__ = ["DeviceRecord", "WaitlistEntry", "DevicePool"]


@dataclass
class DeviceRecord:
    """DeviceRecord."""
    serial: str
    avd_name: str
    status: str = "idle"
    leased_to: str | None = None
    last_heartbeat: float = field(default_factory=time.time)
    auto_restart: bool = True


@dataclass
class WaitlistEntry:
    """Queue entry for device leasing."""
    profile: str
    priority: int
    requested_at: float


class DevicePool:
    """DevicePool."""
    def __init__(self, emulator_bin: str = "/opt/android-sdk/emulator/emulator"):
        """Initialize DevicePool."""
        self.devices: Dict[str, DeviceRecord] = {}
        self.waitlist: List[WaitlistEntry] = []
        self.emulator_bin = emulator_bin

    def register(
        self, serial: str, avd_name: str | None = None, auto_restart: bool = True
    ) -> DeviceRecord:
        """Register a device in the pool with optional AVD name."""
        self.devices[serial] = DeviceRecord(
            serial=serial, avd_name=avd_name or serial, auto_restart=auto_restart
        )
        return self.devices[serial]

    def _restart_emulator(self, record: DeviceRecord) -> bool:
        if not record.auto_restart:
            return False
        try:
            subprocess.Popen(
                [
                    self.emulator_bin,
                    "-avd",
                    record.avd_name,
                    "-no-window",
                    "-no-audio",
                    "-gpu",
                    "swiftshader_indirect",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            record.status = "idle"
            record.leased_to = None
            record.last_heartbeat = time.time()
            return True
        except Exception:
            return False

    def lease(
        self,
        profile: str,
        serial: str | None = None,
        preferred_avd: str | None = None,
    ) -> Optional[DeviceRecord]:
        """Lease a device to a profile, optionally enqueuing if busy."""
        if serial:
            dev = self.devices.get(serial)
            if dev and dev.status == "idle":
                dev.status = "busy"
                dev.leased_to = profile
                dev.last_heartbeat = time.time()
                return dev
            return None

        for dev in self.devices.values():
            if dev.status == "idle":
                if preferred_avd and dev.avd_name != preferred_avd:
                    continue
                dev.status = "busy"
                dev.leased_to = profile
                dev.last_heartbeat = time.time()
                return dev

        for dev in self.devices.values():
            if dev.status == "busy":
                self._restart_emulator(dev)

        return None

    def release(self, profile: str) -> Optional[DeviceRecord]:
        """Release a leased device back to the pool."""
        for dev in self.devices.values():
            if dev.leased_to == profile and dev.status == "busy":
                dev.status = "idle"
                dev.leased_to = None
                return dev
        return None

    def heartbeat(self, serial: str) -> bool:
        """Record a heartbeat for an active device."""
        dev = self.devices.get(serial)
        if not dev:
            return False
        dev.last_heartbeat = time.time()
        return True

    def reap_stale(self, max_silence_s: float = 900) -> list[str]:
        """Mark silent devices as offline."""
        now = time.time()
        released = []
        for dev in list(self.devices.values()):
            if dev.status == "busy" and now - dev.last_heartbeat > max_silence_s:
                self._restart_emulator(dev)
                released.append(dev.serial)
        return released

    def enqueue(self, profile: str, priority: int = 0) -> None:
        """Enqueue a profile on the device waitlist."""
        self.waitlist.append(
            WaitlistEntry(profile=profile, priority=priority, requested_at=time.time())
        )
