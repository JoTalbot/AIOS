"""AIOS Android Base Driver.

Unified Android automation surface. Supports both raw ADB and Appium
backends. All higher-level flows should depend on this interface only.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["DriverCapabilities", "UIContext", "AndroidDriver"]


@dataclass
class DriverCapabilities:
    """Android driver capability flags and settings."""
    package: str = "ua.slando"
    device_name: str = "emulator"
    platform_version: str = "35"
    automation_name: str = "UiAutomator2"
    auto_grant_permissions: bool = True
    no_reset: bool = True
    full_reset: bool = False


@dataclass
    """Snapshot of the current UI state."""
class UIContext:
    xml: str
    package: str
    current_activity: str
    screenshot_path: Optional[str] = None


class AndroidDriver(ABC):
    """Minimal contract both raw ADB and Appium drivers must implement."""

    @abstractmethod
    def launch_app(self) -> bool:
        """Launch the configured package."""

    @abstractmethod
    def dump_ui(self) -> UIContext:
        """Return current UI context."""

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

    @abstractmethod
    def screenshot(self, path: str) -> bool:
        """Capture screenshot."""

    @abstractmethod
    def is_app_installed(self) -> bool:
        """Check package installation status."""

    @abstractmethod
    def current_package(self) -> str:
        """Return current foreground package."""
