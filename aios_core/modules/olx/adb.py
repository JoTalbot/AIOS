"""
AIOS OLX Android Agent
ADB Controller

Управление OLX Android приложением через ADB.
"""

import subprocess
from pathlib import Path
from datetime import datetime


class ADBController:
    def __init__(self, package="ua.slando"):
        self.package = package

    def run(self, command):
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )

        return {
            "code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }

    def swipe(self, x1, y1, x2, y2, duration=500):
        cmd = (
            f"adb shell input swipe "
            f"{x1} {y1} {x2} {y2} {duration}"
        )

        return self.run(cmd)

    def dump_ui(self, filename="screen.xml"):
        remote = "/sdcard/aios_ui.xml"

        self.run(
            f"adb shell uiautomator dump {remote}"
        )

        result = self.run(
            f"adb pull {remote} {filename}"
        )

        return result

    def screenshot(self, filename="screen.png"):
        cmd = (
            f"adb exec-out screencap -p > {filename}"
        )

        return self.run(cmd)

    def open_app(self):
        cmd = (
            f"adb shell monkey "
            f"-p {self.package} 1"
        )

        return self.run(cmd)


if __name__ == "__main__":
    adb = ADBController()

    print(adb.open_app())
    print(adb.dump_ui("olx_ui.xml"))
