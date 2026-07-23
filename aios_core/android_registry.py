"""AIOS Android App Registry (M3).

Declarative multi-app abstraction. Platform descriptor plus optional driver
selection layer supports `ua.slando` plus other apps without changing the
REST API surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from aios_core.android_appium import AppiumAndroidDriver, AppiumDriverConfig
from aios_core.android_driver import AndroidDriver, DriverCapabilities
from aios_core.android_execution import RealDeviceExecutor
from aios_core.platforms.catalog import load_catalog


@dataclass
class AndroidAppDescriptor:
    name: str
    package: str
    backend: str = "adb"
    capabilities: Optional[DriverCapabilities] = None

    def build_driver(self, device_id: Optional[str] = None) -> AndroidDriver:
        if self.backend == "adb":
            return RealDeviceExecutor(device_id=device_id or "emulator-5554")
        if self.backend == "appium":
            cfg = self.capabilities or AppiumDriverConfig(
                package=self.package, device_name=device_id or "emulator"
            )
            return AppiumAndroidDriver(cfg)
        raise ValueError(f"Unsupported backend: {self.backend}")

    def supports(self, action: str) -> bool:
        supported = {
            "ua.slando": {"search", "get_item_details", "send_message"},
            "com.facebook.katana": {"search", "send_message"},
            "com.instagram.android": {"search", "get_item_details"},
        }
        return action in supported.get(self.package, set())


class AndroidAppRegistry:
    def __init__(self):
        self._apps: Dict[str, AndroidAppDescriptor] = {}

    def register(self, descriptor: AndroidAppDescriptor) -> None:
        self._apps[descriptor.package] = descriptor

    def get(self, package: str) -> Optional[AndroidAppDescriptor]:
        return self._apps.get(package)

    def driver_for(self, package: str, device_id: Optional[str] = None) -> Optional[AndroidDriver]:
        desc = self.get(package)
        if desc is None:
            return None
        return desc.build_driver(device_id)

    def load_from_catalog(self, directory: str = "platforms"):
        try:
            descriptors = load_catalog(directory)
        except Exception:
            return
        for descriptor in descriptors:
            try:
                self.register(
                    AndroidAppDescriptor(
                        name=descriptor.name,
                        package=descriptor.android_package,
                        backend="adb",
                    )
                )
            except Exception:
                continue

    def all_packages(self) -> List[str]:
        return list(self._apps.keys())
