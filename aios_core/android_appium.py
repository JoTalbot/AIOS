"""AIOS Android Appium Driver (M2).

Wraps Appium client to satisfy the shared AndroidDriver interface.
Keeps raw ADB path untouched and adds a stable cross-platform automation backend.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from aios_core.android_driver import AndroidDriver, DriverCapabilities, UIContext


@dataclass
class AppiumDriverConfig(DriverCapabilities):
    server_url: str = "http://localhost:4723/wd/hub"


class AppiumAndroidDriver(AndroidDriver):
    def __init__(self, config: Optional[AppiumDriverConfig] = None):
        self.config = config or AppiumDriverConfig()
        self._driver = None

    def start(self) -> bool:
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
            print(f"appium_start_failed: {exc}")
            return False

    def quit(self) -> None:
        if self._driver is not None:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None

    def launch_app(self) -> bool:
        try:
            if self._driver is None:
                return self.start()
            self._driver.activate_app(self.config.package)
            time.sleep(2)
            return True
        except Exception:
            return False

    def dump_ui(self) -> UIContext:
        try:
            if self._driver is None:
                return UIContext(xml="", package=self.config.package, current_activity="")
            xml = self._driver.page_source
            current = ""
            try:
                current = self._driver.current_activity or ""
            except Exception:
                pass
            return UIContext(xml=xml, package=self.config.package, current_activity=current)
        except Exception as exc:
            return UIContext(xml="", package=self.config.package, current_activity="", screenshot_path="")

    def tap(self, x: int, y: int) -> None:
        if self._driver is None:
            return
        self._driver.tap([(x, y)])

    def type_text(self, text: str) -> None:
        if self._driver is None:
            return
        self._driver.execute_script("mobile: type", {"text": text})

    def press_key(self, keycode: int) -> None:
        if self._driver is None:
            return
        try:
            self._driver.press_keycode(keycode)
        except Exception:
            pass

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> None:
        if self._driver is None:
            return
        try:
            self._driver.swipe(x1, y1, x2, y2, duration)
        except Exception:
            pass

    def screenshot(self, path: str) -> bool:
        try:
            if self._driver is None:
                return False
            data = self._driver.get_screenshot_as_png()
            Path(path).write_bytes(data)
            return True
        except Exception:
            return False

    def is_app_installed(self) -> bool:
        try:
            if self._driver is None:
                return False
            return self._driver.is_app_installed(self.config.package)
        except Exception:
            return False

    def current_package(self) -> str:
        try:
            if self._driver is None:
                return self.config.package
            return self._driver.current_package or self.config.package
        except Exception:
            return self.config.package
