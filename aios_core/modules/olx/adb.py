"""
AIOS OLX Android Agent
ADB Controller

Управление OLX Android приложением через ADB.

Контроллер может быть привязан к конкретному устройству/эмулятору через
``serial`` (например ``emulator-5556``): тогда все adb-команды выполняются
с флагом ``-s <serial>``. Это позволяет работать с несколькими
профилями/аккаунтами одновременно — каждый профиль обслуживается своим
устройством из пула (см. ``aios_core.platforms``).
"""

import subprocess
from datetime import datetime
from pathlib import Path


class ADBController:
    def __init__(self, package="ua.slando", serial=None):
        """ADB controller.

        Args:
            package: Android package of the marketplace app.
            serial: Optional device serial (``adb devices``). When set,
                every command is scoped with ``adb -s <serial> ...`` so
                several devices/emulators can be driven in parallel.
        """
        self.package = package
        self.serial = serial

    @property
    def adb(self) -> str:
        """adb binary prefix with optional device selector."""
        if self.serial:
            return f"adb -s {self.serial}"
        return "adb"

    def run(self, command):
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        return {
            "code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }

    def swipe(self, x1, y1, x2, y2, duration=500):
        cmd = f"{self.adb} shell input swipe " f"{x1} {y1} {x2} {y2} {duration}"

        return self.run(cmd)

    def tap(self, x, y):
        return self.run(f"{self.adb} shell input tap {x} {y}")

    def dump_ui(self, filename="screen.xml"):
        remote = "/sdcard/aios_ui.xml"

        self.run(f"{self.adb} shell uiautomator dump {remote}")

        result = self.run(f"{self.adb} pull {remote} {filename}")

        return result

    def screenshot(self, filename="screen.png"):
        cmd = f"{self.adb} exec-out screencap -p > {filename}"

        return self.run(cmd)

    def open_app(self):
        cmd = f"{self.adb} shell monkey " f"-p {self.package} 1"

        return self.run(cmd)

    def input_text(self, text):
        """Types text via the ADBKeyBoard broadcast IME (Cyrillic-safe)."""
        from urllib.parse import quote

        encoded = quote(text, safe="")
        return self.run(f"{self.adb} shell am broadcast " f"-a ADB_INPUT_TEXT --es msg '{encoded}'")


if __name__ == "__main__":
    adb = ADBController()

    print(adb.open_app())
    print(adb.dump_ui("olx_ui.xml"))
