"""AIOS Android Base Driver.

Unified Android automation surface. Supports both raw ADB and Appium
backends. All higher-level flows should depend on this interface only.

Includes the abstract contract plus concrete implementations:
- ``ADBDriver`` — raw ADB command execution for emulator/device control
- ``AppiumDriverWrapper`` — thin Appium-based implementation
- ``DriverPool`` — pool manager for multi-device scenarios
"""

from __future__ import annotations

import os
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

__all__ = [
    "ADBDriver",
    "AndroidDriver",
    "AppiumDriverWrapper",
    "DriverCapabilities",
    "DriverPool",
    "UIContext",
]


@dataclass
class DriverCapabilities:
    """Driver capabilities descriptor."""

    package: str = "ua.slando"
    device_name: str = "emulator"
    platform_version: str = "35"
    automation_name: str = "UiAutomator2"
    auto_grant_permissions: bool = True
    no_reset: bool = True
    full_reset: bool = False


@dataclass
class UIContext:
    """Snapshot of the current UI state."""

    xml: str
    package: str
    current_activity: str
    screenshot_path: str | None = None


class AndroidDriver(ABC):
    """Minimal contract both raw ADB and Appium drivers must implement."""

    # ---- Lifecycle ----

    @abstractmethod
    def launch_app(self) -> bool:
        """Launch the configured package."""

    @abstractmethod
    def close_app(self) -> bool:
        """Close / force-stop the configured package."""

    # ---- UI inspection ----

    @abstractmethod
    def dump_ui(self) -> UIContext:
        """Return current UI context."""

    @abstractmethod
    def screenshot(self, path: str) -> bool:
        """Capture screenshot."""

    # ---- Interaction ----

    @abstractmethod
    def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""

    @abstractmethod
    def type_text(self, text: str) -> None:
        """Type text into focused input."""

    @abstractmethod
    def press_key(self, keycode: int) -> None:
        """Press a key event."""

    @abstractmethod
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> None:
        """Swipe gesture."""

    # ---- Info ----

    @abstractmethod
    def is_app_installed(self) -> bool:
        """Check package installation status."""

    @abstractmethod
    def current_package(self) -> str:
        """Return current foreground package."""

    # ---- Convenience (non-abstract) ----

    def wait_for_app(self, timeout: float = 10.0) -> bool:
        """Poll ``current_package`` until it matches ``capabilities.package``."""
        deadline = time.time() + timeout
        pkg = getattr(self, "capabilities", None)
        target = pkg.package if pkg else ""
        while time.time() < deadline:
            try:
                if self.current_package() == target:
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def safe_tap(self, x: int, y: int, retries: int = 3) -> bool:
        """Tap with retry on failure."""
        for i in range(retries):
            try:
                self.tap(x, y)
                return True
            except Exception:
                if i == retries - 1:
                    return False
                time.sleep(0.3)
        return False


class ADBDriver(AndroidDriver):
    """Concrete driver that executes raw ADB shell commands.

    This is a lightweight implementation that delegates to ``adb`` CLI
    commands.  It requires ADB to be installed and a device/emulator
    to be connected.
    """

    def __init__(
        self,
        capabilities: DriverCapabilities | None = None,
        device_id: str = "",
        adb_path: str = "adb",
    ):
        """Initialize ADBDriver."""
        self.capabilities = capabilities or DriverCapabilities()
        self.device_id = device_id
        self.adb_path = adb_path
        self._connected = False

    def _adb(self, *args: str) -> str:
        """Run an adb command and return stdout."""
        cmd = [self.adb_path]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return result.stdout.strip()
        except Exception:
            return ""

    # ---- Lifecycle ----

    def launch_app(self) -> bool:
        """Launch the configured package via ``adb shell am start``."""
        pkg = self.capabilities.package
        output = self._adb("shell", "am", "start", "-n", f"{pkg}/.MainActivity")
        return "Error" not in output

    def close_app(self) -> bool:
        """Force-stop the configured package."""
        self._adb("shell", "am", "force-stop", self.capabilities.package)
        return True

    # ---- UI inspection ----

    def dump_ui(self) -> UIContext:
        """Dump UI hierarchy via ``adb shell uiautomator dump``."""
        xml = self._adb("shell", "uiautomator", "dump", "/dev/tty")
        pkg = self.current_package()
        activity = self._adb("shell", "dumpsys", "activity", "activities")
        # Parse current activity from dumpsys
        current = ""
        for line in activity.split("\n"):
            if "mResumedActivity" in line or "mFocusedActivity" in line:
                parts = line.strip().split()
                for p in parts:
                    if "/" in p:
                        current = p
                        break
                break
        return UIContext(xml=xml, package=pkg, current_activity=current)

    def screenshot(self, path: str) -> bool:
        """Capture screenshot via adb."""
        remote = "/sdcard/aios_screenshot.png"
        self._adb("shell", "screencap", "-p", remote)
        self._adb("pull", remote, path)
        self._adb("shell", "rm", remote)
        return os.path.exists(path)

    # ---- Interaction ----

    def tap(self, x: int, y: int) -> None:
        """Tap at (x, y) via ``adb shell input tap``."""
        self._adb("shell", "input", "tap", str(x), str(y))

    def type_text(self, text: str) -> None:
        """Type text via ``adb shell input text``."""
        # Escape spaces for adb
        escaped = text.replace(" ", "%s").replace("&", "\\&")
        self._adb("shell", "input", "text", escaped)

    def press_key(self, keycode: int) -> None:
        """Press a key event via adb."""
        self._adb("shell", "input", "keyevent", str(keycode))

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> None:
        """Swipe via ``adb shell input swipe``."""
        self._adb(
            "shell",
            "input",
            "swipe",
            str(x1),
            str(y1),
            str(x2),
            str(y2),
            str(duration),
        )

    # ---- Info ----

    def is_app_installed(self) -> bool:
        """Check if package is installed."""
        output = self._adb("shell", "pm", "list", "packages", self.capabilities.package)
        return self.capabilities.package in output

    def current_package(self) -> str:
        """Return current foreground package."""
        output = self._adb("shell", "dumpsys", "window", "windows")
        for line in output.split("\n"):
            if "mCurrentFocus" in line or "mFocusedApp" in line:
                for part in line.strip().split():
                    if "/" in part:
                        return part.split("/")[0]
        return ""

    def list_devices(self) -> list[str]:
        """Return list of connected ADB device serials."""
        output = self._adb("devices")
        lines = [l for l in output.split("\n") if l.strip() and "List" not in l]
        return [l.split()[0] for l in lines if "device" in l]

    def install_apk(self, apk_path: str) -> bool:
        """Install an APK onto the device."""
        output = self._adb("install", "-r", apk_path)
        return "Success" in output


class AppiumDriverWrapper(AndroidDriver):
    """Thin Appium-based implementation for Selenium/Appium users.

    This wraps the AppiumAndroidDriver from android_appium.py,
    translating the abstract interface calls into Appium operations.
    """

    def __init__(
        self,
        capabilities: DriverCapabilities | None = None,
        appium_driver: Any = None,
    ):
        """Initialize AppiumDriverWrapper."""
        self.capabilities = capabilities or DriverCapabilities()
        self._appium = appium_driver

    def _require_appium(self) -> Any:
        """Raise if no Appium driver is bound."""
        if self._appium is None:
            raise RuntimeError(
                "No Appium driver attached — provide one or use ADBDriver"
            )
        return self._appium

    # ---- Lifecycle ----

    def launch_app(self) -> bool:
        """Launch app via Appium driver."""
        try:
            driver = self._require_appium()
            driver.launch_app()
            return True
        except Exception:
            return False

    def close_app(self) -> bool:
        """Close app via Appium."""
        try:
            driver = self._require_appium()
            driver.close_app()
            return True
        except Exception:
            return False

    # ---- UI inspection ----

    def dump_ui(self) -> UIContext:
        """Get UI context via Appium page source."""
        driver = self._require_appium()
        xml = driver.page_source
        return UIContext(
            xml=xml, package=self.capabilities.package, current_activity=""
        )

    def screenshot(self, path: str) -> bool:
        """Screenshot via Appium."""
        try:
            driver = self._require_appium()
            driver.save_screenshot(path)
            return os.path.exists(path)
        except Exception:
            return False

    # ---- Interaction ----

    def tap(self, x: int, y: int) -> None:
        """Tap via Appium actions."""
        driver = self._require_appium()
        driver.tap([(x, y)])

    def type_text(self, text: str) -> None:
        """Type via Appium send_keys."""
        driver = self._require_appium()
        element = driver.find_element_by_class_name("android.widget.EditText")
        if element:
            element.send_keys(text)

    def press_key(self, keycode: int) -> None:
        """Press key via Appium key event."""
        driver = self._require_appium()
        driver.keyevent(keycode)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> None:
        """Swipe via Appium swipe."""
        driver = self._require_appium()
        driver.swipe(x1, y1, x2, y2, duration)

    # ---- Info ----

    def is_app_installed(self) -> bool:
        """Check installation via Appium."""
        driver = self._require_appium()
        return driver.is_app_installed(self.capabilities.package)

    def current_package(self) -> str:
        """Get current package via Appium."""
        driver = self._require_appium()
        return driver.current_package


class DriverPool:
    """Pool manager for multi-device Android testing scenarios.

    Maintains a collection of AndroidDriver instances, one per device,
    and provides round-robin or least-load dispatch for parallel runs.
    """

    def __init__(self):
        """Initialize DriverPool."""
        self._drivers: dict[str, AndroidDriver] = {}
        self._dispatch_counts: dict[str, int] = {}

    def add_driver(self, device_id: str, driver: AndroidDriver) -> None:
        """Register a driver under *device_id*."""
        self._drivers[device_id] = driver
        self._dispatch_counts[device_id] = 0

    def remove_driver(self, device_id: str) -> bool:
        """Remove a driver from the pool."""
        if device_id not in self._drivers:
            return False
        driver = self._drivers.pop(device_id)
        self._dispatch_counts.pop(device_id, None)
        try:
            driver.close_app()
        except Exception:
            pass
        return True

    def get_driver(self, device_id: str) -> AndroidDriver | None:
        """Retrieve a specific driver."""
        return self._drivers.get(device_id)

    def dispatch(self, strategy: str = "round_robin") -> AndroidDriver | None:
        """Select a driver using *strategy* ('round_robin' or 'least_used')."""
        if not self._drivers:
            return None
        if strategy == "round_robin":
            device_id = min(self._dispatch_counts, key=self._dispatch_counts.get)
        elif strategy == "least_used":
            device_id = min(
                self._dispatch_counts, key=lambda k: self._dispatch_counts[k]
            )
        else:
            device_id = next(iter(self._drivers))

        self._dispatch_counts[device_id] += 1
        return self._drivers[device_id]

    def all_launch(self) -> dict[str, bool]:
        """Launch apps on all pooled drivers."""
        results = {}
        for device_id, driver in self._drivers.items():
            try:
                results[device_id] = driver.launch_app()
            except Exception:
                results[device_id] = False
        return results

    def all_close(self) -> dict[str, bool]:
        """Close apps on all pooled drivers."""
        results = {}
        for device_id, driver in self._drivers.items():
            try:
                results[device_id] = driver.close_app()
            except Exception:
                results[device_id] = False
        return results

    def stats(self) -> dict[str, Any]:
        """Return pool statistics."""
        return {
            "pool_size": len(self._drivers),
            "devices": list(self._drivers.keys()),
            "dispatch_counts": dict(self._dispatch_counts),
        }
