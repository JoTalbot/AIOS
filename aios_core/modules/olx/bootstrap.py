"""AIOS OLX Android Agent — environment bootstrap for a *fresh server*.

Generates (and, with ``execute=True``, runs) the full setup needed for OLX
automation: Android platform-tools, Python deps, ADBKeyBoard for Cyrillic
input, and — optionally — a headless Android emulator (cmdline-tools,
system image, AVD) with OLX installed.

Also provides ``doctor()``: a readiness checklist reported step by step.
Everything is DRY-RUN by default; the runner is injectable for tests.

Usage via CLI: ``aios olx bootstrap [--execute] [--emulator] [--apk app.apk]``
and readiness check: ``aios olx doctor``.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

PLATFORM_TOOLS_URL = (
    "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
)
CMDLINE_TOOLS_URL = (
    "https://dl.google.com/android/repository/"
    "commandlinetools-linux-11076708_latest.zip"
)
ADBKEYBOARD_URL = "https://github.com/senzhk/ADBKeyBoard/raw/master/ADBKeyboard.apk"
SDK_ROOT = "/opt/android-sdk"
SYSTEM_IMAGE = "system-images;android-34;google_apis;x86_64"
AVD_NAME = "aios-olx"


def _shell_runner(command: list[str], timeout: int = 600) -> dict[str, object]:
    try:
        result = subprocess.run(
            command,
            shell=isinstance(command, str),
            capture_output=True,
            text=True,
            timeout=timeout,
            executable="/bin/bash",
        )
        return {
            "code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except Exception as exc:  # command missing, timeout, etc.
        return {"code": 127, "stdout": "", "stderr": str(exc)}


@dataclass
class BootstrapStep:
    """BootstrapStep."""

    name: str
    why: str
    commands: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {"name": self.name, "why": self.why, "commands": list(self.commands)}


@dataclass
class DoctorCheck:
    """DoctorCheck."""

    name: str
    ok: bool
    hint: str = ""

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {"name": self.name, "ok": self.ok, "hint": self.hint}


class OLXBootstrap:
    """Plans/executes the fresh-server setup and verifies readiness."""

    def __init__(
        self,
        runner: Callable[[list[str]], dict[str, object]] | None = None,
        project_root: str = ".",
        workdir: str = "/opt/aios-olx",
    ):
        """Initialize OLXBootstrap."""
        self.runner = runner or _shell_runner
        self.project_root = Path(project_root)
        self.workdir = workdir

    # ---------------- plan ----------------

    def plan(
        self,
        emulator: bool = True,
        apt: bool = True,
        olx_apk: str | None = None,
    ) -> list[BootstrapStep]:
        """Ordered setup plan for a fresh Linux server."""
        steps: list[BootstrapStep] = []

        if apt:
            steps.append(
                BootstrapStep(
                    "apt-packages",
                    "Базові системні пакети (архіватори, Java для SDK tools)",
                    [
                        "sudo apt-get update -y",
                        "sudo apt-get install -y wget unzip curl default-jre-headless",
                    ],
                )
            )

        steps.append(
            BootstrapStep(
                "python-deps",
                "Залежності проєкту (тести та OLX-модуль)",
                [f"python3 -m pip install -r {self.project_root}/requirements.txt"],
            )
        )

        steps.append(
            BootstrapStep(
                "platform-tools",
                "ADB/fastboot — керування пристроями й емулятором",
                [
                    f"sudo mkdir -p {self.workdir} && sudo chown $USER {self.workdir}",
                    f"wget -q {PLATFORM_TOOLS_URL} -O {self.workdir}/platform-tools.zip",
                    f"unzip -o -q {self.workdir}/platform-tools.zip -d {self.workdir}",
                    f"export PATH=$PATH:{self.workdir}/platform-tools",
                    "adb version",
                ],
            )
        )

        steps.append(
            BootstrapStep(
                "adbkeyboard-apk",
                "ADBKeyBoard — введення кирилиці через broadcast",
                [f"wget -q {ADBKEYBOARD_URL} -O {self.workdir}/ADBKeyboard.apk"],
            )
        )

        if emulator:
            steps.append(
                BootstrapStep(
                    "sdk-cmdline-tools",
                    "Android SDK cmdline-tools — керування образами й AVD",
                    [
                        f"wget -q {CMDLINE_TOOLS_URL} -O {self.workdir}/cmdline-tools.zip",
                        f"sudo mkdir -p {SDK_ROOT}/cmdline-tools && "
                        f"unzip -o -q {self.workdir}/cmdline-tools.zip -d {self.workdir}/cmdline-tools",
                        f"sudo mkdir -p {SDK_ROOT}/cmdline-tools/latest && "
                        f"sudo cp -r {self.workdir}/cmdline-tools/cmdline-tools/* "
                        f"{SDK_ROOT}/cmdline-tools/latest/",
                    ],
                )
            )
            steps.append(
                BootstrapStep(
                    "sdk-packages",
                    "Емулятор + системний образ Android 34 (x86_64)",
                    [
                        f"yes | {SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager --licenses",
                        f"{SDK_ROOT}/cmdline-tools/latest/bin/sdkmanager "
                        f"'platform-tools' 'emulator' '{SYSTEM_IMAGE}'",
                    ],
                )
            )
            steps.append(
                BootstrapStep(
                    "create-avd",
                    f"Створити headless-AVD «{AVD_NAME}»",
                    [
                        f"echo no | {SDK_ROOT}/cmdline-tools/latest/bin/avdmanager "
                        f"create avd -n {AVD_NAME} -k '{SYSTEM_IMAGE}' --device 'pixel_6'"
                    ],
                )
            )
            steps.append(
                BootstrapStep(
                    "start-emulator",
                    "Запуск емулятора у фоні (headless) й очікування завантаження",
                    [
                        f"nohup {SDK_ROOT}/emulator/emulator -avd {AVD_NAME} "
                        f"-no-window -no-audio -no-snapshot-save &",
                        "adb wait-for-device",
                        "adb shell 'while [[ -z $(getprop sys.boot_completed) ]]; do "
                        "sleep 2; done'",
                    ],
                )
            )

        steps.append(
            BootstrapStep(
                "device-setup",
                "Установка ADBKeyBoard та OLX на пристрій; IME для кирилиці",
                (
                    [f"adb install -r {self.workdir}/ADBKeyboard.apk"]
                    + (
                        [f"adb install -r {olx_apk}"]
                        if olx_apk
                        else [
                            "# Встановіть OLX: adb install -r olx.apk (або з Play Store вручну)"
                        ]
                    )
                    + [
                        "adb shell ime set com.android.adbkeyboard/.AdbIME",
                        "adb shell pm list packages | grep -i slando",
                    ]
                ),
            )
        )

        steps.append(
            BootstrapStep(
                "verify",
                "Перевірка готовності (doctor)",
                [f"python3 {self.project_root}/aios_cli.py olx doctor"],
            )
        )
        return steps

    def print_plan(self, **kwargs) -> str:
        """Execute print plan."""
        lines: list[str] = []
        for index, step in enumerate(self.plan(**kwargs), start=1):
            lines.append(f"{index}. {step.name} — {step.why}")
            lines.extend(f"   $ {command}" for command in step.commands)
        return "\n".join(lines)

    def execute(self, **kwargs) -> list[dict[str, object]]:
        """Run the plan step by step. Returns per-command results."""
        results: list[dict[str, object]] = []
        for step in self.plan(**kwargs):
            for command in step.commands:
                if command.startswith("#"):
                    continue
                outcome = self.runner(command)
                results.append({"step": step.name, "command": command, **outcome})
                if outcome.get("code") not in (0, None):
                    results.append(
                        {
                            "step": step.name,
                            "command": command,
                            "code": outcome.get("code"),
                            "aborted": True,
                        }
                    )
                    return results
        return results

    # ---------------- doctor ----------------

    def doctor(self, db_path: str = ":memory:") -> list[DoctorCheck]:
        """Readiness checklist; each item carries a fix hint when failing."""
        checks: list[DoctorCheck] = []

        adb = self.runner("adb version")
        adb_ok = adb.get("code") == 0
        checks.append(
            DoctorCheck(
                "adb_installed",
                adb_ok,
                (
                    ""
                    if adb_ok
                    else "Встановіть platform-tools (bootstrap: platform-tools)"
                ),
            )
        )

        if adb_ok:
            devices = self.runner("adb devices")
            lines = str(devices.get("stdout", "")).splitlines()[1:]
            online = [line for line in lines if line.strip().endswith("\tdevice")]
            checks.append(
                DoctorCheck(
                    "device_online",
                    bool(online),
                    (
                        ""
                        if online
                        else "Підключіть телефон або запустіть емулятор "
                        f"(bootstrap: start-emulator → AVD {AVD_NAME})"
                    ),
                )
            )
            if online:
                packages = self.runner("adb shell pm list packages")
                has_olx = "slando" in str(packages.get("stdout", "")).lower()
                checks.append(
                    DoctorCheck(
                        "olx_installed",
                        has_olx,
                        "" if has_olx else "Встановіть OLX: adb install -r olx.apk",
                    )
                )
                ime = self.runner("adb shell settings get secure default_input_method")
                ime_ok = "adbkeyboard" in str(ime.get("stdout", "")).lower()
                checks.append(
                    DoctorCheck(
                        "adbkeyboard_ime",
                        ime_ok,
                        (
                            ""
                            if ime_ok
                            else "adb shell ime set com.android.adbkeyboard/.AdbIME"
                        ),
                    )
                )

        try:
            import aios_core.modules.olx

            checks.append(DoctorCheck("python_module", True))
        except Exception as exc:
            checks.append(
                DoctorCheck("python_module", False, f"pip install -e . ({exc})")
            )

        try:
            from .storage import OLXStorage

            storage = OLXStorage(db_path)
            storage.close()
            checks.append(DoctorCheck("storage_writable", True))
        except Exception as exc:
            checks.append(DoctorCheck("storage_writable", False, str(exc)))

        return checks

    def doctor_report(self, db_path: str = ":memory:") -> dict[str, object]:
        """Execute doctor report."""
        checks = self.doctor(db_path=db_path)
        ok = all(check.ok for check in checks)
        return {"ready": ok, "checks": [check.to_dict() for check in checks]}
