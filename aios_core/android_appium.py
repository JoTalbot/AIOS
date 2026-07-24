"""AIOS Android Appium Driver (M2).

Wraps Appium client to satisfy the shared AndroidDriver interface.
Supports UiAutomator2 + XPath selectors and scenario playback hooks.
Keeps raw ADB path untouched and adds a stable cross-platform automation backend.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

from aios_core.android_driver import AndroidDriver, DriverCapabilities, UIContext

__all__ = ["AppiumDriverConfig", "AppiumAndroidDriver"]

logger = logging.getLogger(__name__)


@dataclass
class AppiumDriverConfig(DriverCapabilities):
    """Appium driver configuration parameters."""
    server_url: str = "http://localhost:4723/wd/hub"
    automation_name: str = "UiAutomator2"


    """Appium-based Android automation driver."""
class AppiumAndroidDriver(AndroidDriver):
    """AppiumAndroidDriver."""
    def __init__(self, config: Optional[AppiumDriverConfig] = None):
        """Initialize AppiumAndroidDriver."""
        self.config = config or AppiumDriverConfig()
        self._driver = None

    def start(self) -> bool:
        """Execute start."""
        try:
            from appium import webdriver

            self._driver = webdriver.Remote(
                command_executor=self.config.server_url,
                desired_capabilities={
                    "platformName": "Android",
                    "automationName": self.config.automation_name,
                    "platformVersion": self.config.platform_version,
                    "deviceName": self.config.device_name,
                    "appPackage": self.config.package,
                    "autoGrantPermissions": self.config.auto_grant_permissions,
                    "noReset": self.config.no_reset,
                    "fullReset": self.config.full_reset,
                },
            )
            return True
        except Exception as exc:
            logger.error("appium_start_failed: %s", exc)
            return False

    def quit(self) -> None:
        """Execute quit."""
        if self._driver is not None:
            try:
                self._driver.quit()
            except Exception:
                pass  # Best-effort cleanup — ignore if already disconnected
            self._driver = None

    def launch_app(self) -> bool:
        """Execute launch app."""
        try:
            if self._driver is None:
                return self.start()
            self._driver.activate_app(self.config.package)
            time.sleep(2)
            return True
        except Exception:
            return False  # Appium session may be stale

    def dump_ui(self) -> UIContext:
        """Execute dump ui."""
        try:
            if self._driver is None:
                return UIContext(xml="", package=self.config.package, current_activity="")
            xml = self._driver.page_source
            current = ""
            try:
                current = self._driver.current_activity or ""
            except Exception:
                pass  # current_activity is best-effort metadata
            return UIContext(xml=xml, package=self.config.package, current_activity=current)
        except Exception as exc:
            return UIContext(
                xml="",
                package=self.config.package,
                current_activity="",
                screenshot_path="",
            )

    def tap(self, x: int, y: int) -> None:
        """Execute tap."""
        if self._driver is None:
            return
        self._driver.tap([(x, y)])

    def type_text(self, text: str) -> None:
        """Execute type text."""
        if self._driver is None:
            return
        self._driver.execute_script("mobile: type", {"text": text})

    def press_key(self, keycode: int) -> None:
        """Execute press key."""
        if self._driver is None:
            return
        try:
            self._driver.press_keycode(keycode)
        except Exception:
            pass  # Key injection can fail on some devices/OS versions

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> None:
        """Execute swipe."""
        if self._driver is None:
            return
        try:
            self._driver.swipe(x1, y1, x2, y2, duration)
        except Exception:
            pass  # Swipe is best-effort; geometry may be off-screen

    def screenshot(self, path: str) -> bool:
        """Execute screenshot."""
        try:
            if self._driver is None:
                return False
            data = self._driver.get_screenshot_as_png()
            Path(path).write_bytes(data)
            return True
        except Exception:
            return False

    def is_app_installed(self) -> bool:
        """Execute is app installed."""
        try:
            if self._driver is None:
                return False
            return self._driver.is_app_installed(self.config.package)
        except Exception:
            return False

    def current_package(self) -> str:
        """Execute current package."""
        try:
            if self._driver is None:
                return self.config.package
            return self._driver.current_package or self.config.package
        except Exception:
            return self.config.package

    def find_element_by_xpath(self, xpath: str) -> Optional[Any]:
        """Execute find element by xpath."""
        if self._driver is None:
            return None
        try:
            return self._driver.find_element_by_xpath(xpath)
        except Exception:
            return None

    def find_elements_by_xpath(self, xpath: str) -> list[Any]:
        """Execute find elements by xpath."""
        if self._driver is None:
            return []
        try:
            return self._driver.find_elements_by_xpath(xpath)
        except Exception:
            return []

    def find_element(self, by: str, value: str) -> Optional[Any]:
        """Execute find element."""
        if self._driver is None:
            return None
        try:
            from appium.webdriver.common.appiumby import AppiumBy

            by_map = {
                "id": AppiumBy.ID,
                "accessibility_id": AppiumBy.ACCESSIBILITY_ID,
                "xpath": AppiumBy.XPATH,
            }
            by_enum = by_map.get(by, AppiumBy.XPATH)
            return self._driver.find_element(by_enum, value)
        except Exception:
            return None
