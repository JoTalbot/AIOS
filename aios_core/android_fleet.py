"""AIOS Android Device Fleet (M4).

Device pool: lease/release/heartbeat/sticky route across emulators/devices.
Each profile can be bound to a dedicated device serial for parallel automation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DeviceRecord:
    serial: str
    avd_name: str
    status: str = "idle"
    leased_to: Optional[str] = None
    last_heartbeat: float = field(default_factory=time.time)


@dataclass
class WaitlistEntry:
    profile: str
    priority: int
    requested_at: float


class DevicePool:
    def __init__(self):
        self.devices: Dict[str, DeviceRecord] = {}
        self.waitlist: List[WaitlistEntry] = []

    def register(self, serial: str, avd_name: Optional[str] = None) -> DeviceRecord:
        self.devices[serial] = DeviceRecord(serial=serial, avd_name=avd_name or serial)
        return self.devices[serial]

    def lease(self, profile: str, serial: Optional[str] = None) -> Optional[DeviceRecord]:
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
                dev.status = "busy"
                dev.leased_to = profile
                dev.last_heartbeat = time.time()
                return dev
        return None

    def release(self, profile: str) -> Optional[DeviceRecord]:
        for dev in self.devices.values():
            if dev.leased_to == profile and dev.status == "busy":
                dev.status = "idle"
                dev.leased_to = None
                return dev
        return None

    def heartbeat(self, serial: str) -> bool:
        dev = self.devices.get(serial)
        if not dev:
            return False
        dev.last_heartbeat = time.time()
        return True

    def reap_stale(self, max_silence_s: float = 900) -> List[str]:
        now = time.time()
        released = []
        for dev in self.devices.values():
            if dev.status == "busy" and now - dev.last_heartbeat > max_silence_s:
                dev.status = "idle"
                dev.leased_to = None
                released.append(dev.serial)
        return released

    def enqueue(self, profile: str, priority: int = 0):
        self.waitlist.append(WaitlistEntry(profile=profile, priority=priority, requested_at=time.time()))
