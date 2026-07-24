"""AIOS Android App Registry (M3).

Declarative multi-app abstraction. Platform descriptor plus optional driver
selection layer supports `ua.slando` plus other apps without changing the
REST API surface.

Features:
- App registration with backend selection (ADB, Appium)
- Driver instantiation per package
- Health monitoring and driver pooling
- Session management with lifecycle tracking
- Platform catalog loading
- Capability matching and action routing
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aios_core.android_appium import AppiumAndroidDriver, AppiumDriverConfig
from aios_core.android_driver import AndroidDriver, DriverCapabilities
from aios_core.android_execution import RealDeviceExecutor
from aios_core.platforms.catalog import load_catalog

__all__ = ["AndroidAppDescriptor", "AndroidAppRegistry", "AndroidSession"]


# Action routing table: which package supports which actions
_ACTION_ROUTING: Dict[str, set[str]] = {
    "ua.slando": {"search", "get_item_details", "send_message", "list_items"},
    "com.facebook.katana": {"search", "send_message", "get_profile"},
    "com.instagram.android": {"search", "get_item_details", "share"},
    "com.whatsapp": {"send_message", "search"},
    "com.twitter.android": {"search", "send_message", "get_profile"},
}


@dataclass
class AndroidAppDescriptor:
    """Descriptor for a registered Android application."""

    name: str
    package: str
    backend: str = "adb"
    capabilities: Optional[DriverCapabilities] = None
    version: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def build_driver(self, device_id: str | None = None) -> AndroidDriver:
        """Construct an appropriate driver instance."""
        if self.backend == "adb":
            return RealDeviceExecutor(device_id=device_id or "emulator-5554")
        if self.backend == "appium":
            cfg = self.capabilities or AppiumDriverConfig(
                package=self.package, device_name=device_id or "emulator"
            )
            return AppiumAndroidDriver(cfg)
        raise ValueError(f"Unsupported backend: {self.backend}")

    def supports(self, action: str) -> bool:
        """Check whether this package supports *action*."""
        supported = _ACTION_ROUTING.get(self.package, set())
        return action in supported

    def supported_actions(self) -> set[str]:
        """Return all supported actions for this package."""
        return set(_ACTION_ROUTING.get(self.package, set()))

    def match_tags(self, query_tags: List[str]) -> bool:
        """Check whether any of *query_tags* match this descriptor's tags."""
        return any(tag in self.tags for tag in query_tags)


@dataclass
class AndroidSession:
    """Active session tracking for a driver instance."""

    session_id: str
    package: str
    device_id: str
    driver: Optional[AndroidDriver] = None
    started_at: float = 0.0
    status: str = "active"

    def duration(self) -> float:
        """Return session duration in seconds."""
        return time.time() - self.started_at

    def close(self) -> None:
        """Mark session as closed and release driver."""
        self.status = "closed"
        if self.driver:
            try:
                self.driver.close_app()
            except Exception:
                pass
        self.driver = None


class AndroidAppRegistry:
    """Registry of Android applications known to AIOS.

    Features:
    - App descriptor registration and lookup
    - Driver instantiation per package and device
    - Session lifecycle management
    - Health monitoring of active drivers
    - Platform catalog loading
    - Action routing to appropriate packages
    """

    def __init__(self):
        """Initialize AndroidAppRegistry."""
        self._apps: Dict[str, AndroidAppDescriptor] = {}
        self._sessions: Dict[str, AndroidSession] = {}
        self._driver_pool: Dict[str, AndroidDriver] = {}
        self._session_counter: int = 0

    # ------------------------------------------------------------------
    # App registration
    # ------------------------------------------------------------------

    def register(self, descriptor: AndroidAppDescriptor) -> None:
        """Register an app descriptor by package name."""
        self._apps[descriptor.package] = descriptor

    def unregister(self, package: str) -> bool:
        """Remove an app from the registry."""
        return self._apps.pop(package, None) is not None

    def get(self, package: str) -> Optional[AndroidAppDescriptor]:
        """Retrieve descriptor by package name."""
        return self._apps.get(package)

    def find_by_action(self, action: str) -> List[AndroidAppDescriptor]:
        """Find all descriptors that support *action*."""
        return [
            desc for desc in self._apps.values()
            if desc.supports(action)
        ]

    def find_by_tags(self, tags: List[str]) -> List[AndroidAppDescriptor]:
        """Find descriptors matching any of *tags*."""
        return [
            desc for desc in self._apps.values()
            if desc.match_tags(tags)
        ]

    # ------------------------------------------------------------------
    # Driver management
    # ------------------------------------------------------------------

    def driver_for(
        self, package: str, device_id: str | None = None
    ) -> Optional[AndroidDriver]:
        """Create or retrieve a cached driver for *package*."""
        desc = self.get(package)
        if desc is None:
            return None

        # Check pool for existing driver
        pool_key = f"{package}:{device_id or 'default'}"
        if pool_key in self._driver_pool:
            return self._driver_pool[pool_key]

        driver = desc.build_driver(device_id)
        self._driver_pool[pool_key] = driver
        return driver

    def release_driver(self, package: str, device_id: str | None = None) -> bool:
        """Remove a pooled driver, closing it first."""
        pool_key = f"{package}:{device_id or 'default'}"
        driver = self._driver_pool.pop(pool_key, None)
        if driver is None:
            return False
        try:
            driver.close_app()
        except Exception:
            pass
        return True

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def create_session(
        self,
        package: str,
        device_id: str = "emulator-5554",
    ) -> AndroidSession:
        """Create a new session with driver for *package*."""
        self._session_counter += 1
        session_id = f"session_{self._session_counter}"
        driver = self.driver_for(package, device_id)

        session = AndroidSession(
            session_id=session_id,
            package=package,
            device_id=device_id,
            driver=driver,
            started_at=time.time(),
        )

        if driver:
            try:
                driver.launch_app()
            except Exception:
                session.status = "error"

        self._sessions[session_id] = session
        return session

    def close_session(self, session_id: str) -> bool:
        """Close and remove a session."""
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session.close()
        self._sessions.pop(session_id, None)
        return True

    def get_session(self, session_id: str) -> Optional[AndroidSession]:
        """Retrieve a session by ID."""
        return self._sessions.get(session_id)

    def active_sessions(self) -> List[AndroidSession]:
        """Return all active sessions."""
        return [
            s for s in self._sessions.values()
            if s.status == "active"
        ]

    # ------------------------------------------------------------------
    # Health monitoring
    # ------------------------------------------------------------------

    def check_driver_health(self, package: str) -> dict[str, Any]:
        """Check whether the pooled driver for *package* is responsive."""
        pool_key = f"{package}:default"
        driver = self._driver_pool.get(pool_key)
        if driver is None:
            return {"healthy": False, "error": "No driver in pool"}

        try:
            installed = driver.is_app_installed()
            return {"healthy": installed, "app_installed": installed}
        except Exception as exc:
            return {"healthy": False, "error": str(exc)}

    def health_report(self) -> Dict[str, dict[str, Any]]:
        """Generate health status for all pooled drivers."""
        report: Dict[str, dict[str, Any]] = {}
        for pool_key, driver in self._driver_pool.items():
            package = pool_key.split(":")[0]
            try:
                installed = driver.is_app_installed()
                report[pool_key] = {"healthy": installed, "app_installed": installed}
            except Exception as exc:
                report[pool_key] = {"healthy": False, "error": str(exc)}
        return report

    # ------------------------------------------------------------------
    # Platform catalog
    # ------------------------------------------------------------------

    def load_from_catalog(self, directory: str = "platforms") -> None:
        """Load app descriptors from platform catalog."""
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

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def all_packages(self) -> list[str]:
        """Return all registered package names."""
        return list(self._apps.keys())

    def all_apps(self) -> List[AndroidAppDescriptor]:
        """Return all registered descriptors."""
        return list(self._apps.values())

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return registry statistics."""
        active = sum(1 for s in self._sessions.values() if s.status == "active")
        return {
            "registered_apps": len(self._apps),
            "active_sessions": active,
            "total_sessions": self._session_counter,
            "pooled_drivers": len(self._driver_pool),
            "packages": self.all_packages(),
        }
