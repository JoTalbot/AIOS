"""Pytest fixtures for Android emulator and ua.slando automation."""

from __future__ import annotations

import os
import subprocess
import time

import pytest

# AIOS prefers stable ua.slando tests on emulator-5554
os.environ.setdefault("AIOS_DEVICE_ID", "emulator-5554")


def _adb(command: str, device_id: str) -> int:
    return subprocess.run(
        ["adb", "-s", device_id, *command.split()],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode


def _wait_for_device(device_id: str, timeout_s: int = 300) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if os.environ.get("AIOS_EMULATOR_HEADLESS") == "1":
            raw = subprocess.run(
                ["adb", "-s", device_id, "shell", "getprop", "sys.boot_completed"],
                capture_output=True,
                text=True,
            )
            if raw.stdout.strip() == "1":
                return True
        else:
            out = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
            )
            if f"{device_id}\tdevice" in out.stdout:
                return True
        time.sleep(2)
    return False


@pytest.fixture(scope="session")
def emulator_process():
    avd = os.environ.get("AIOS_AVD_NAME", "AIOS_OLX")
    emulator_bin = os.environ.get("ANDROID_SDK_ROOT", "/opt/android-sdk") + "/emulator/emulator"
    proc = None
    if os.environ.get("AIOS_EMULATOR_HEADLESS") == "1":
        proc = subprocess.Popen(
            [
                emulator_bin,
                "-avd",
                avd,
                "-no-window",
                "-no-audio",
                "-gpu",
                "swiftshader_indirect",
                "-netdelay",
                "none",
                "-netspeed",
                "full",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    try:
        yield proc
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()


@pytest.fixture(scope="session")
def android_device(emulator_process):
    device_id = os.environ.get("AIOS_DEVICE_ID", "emulator-5554")
    os.environ.setdefault("AIOS_DEVICE_ID", device_id)
    if not _wait_for_device(device_id, timeout_s=420):
        raise RuntimeError(f"Android device {device_id} is not ready")
    return device_id


@pytest.fixture()
def real_executor(android_device):
    from aios_core.android_execution import RealDeviceExecutor

    return RealDeviceExecutor(device_id=os.environ["AIOS_DEVICE_ID"])


@pytest.fixture()
def android_registry():
    from aios_core.android_registry import AndroidAppRegistry

    registry = AndroidAppRegistry()
    registry.register(
        type(
            "Descriptor",
            (),
            {"name": "slando", "package": "ua.slando", "backend": "adb"},
        )()
    )
    return registry
