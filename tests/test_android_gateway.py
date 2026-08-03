"""Тесты безопасного real-Android gateway без реального устройства."""
from __future__ import annotations

import subprocess


def _result(args, stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(args=args, returncode=returncode, stdout=stdout, stderr=stderr)


def test_register_and_status_with_mocked_adb(tmp_path, monkeypatch):
    from aios_core.android_gateway import AndroidGateway

    endpoint = "10.203.0.2:43325"
    gateway = AndroidGateway(tmp_path, adb_bin="adb")

    def fake_run(args, timeout=30, serial=None):
        if args[:2] == ["devices", "-l"]:
            return _result(args, f"List of devices attached\n{endpoint}\tdevice model:G1\n")
        if args[:2] == ["shell", "getprop"]:
            return _result(args, "G1\n" if args[-1] == "ro.product.model" else "15\n")
        if args == ["get-state"]:
            return _result(args, "device\n")
        if args[:2] == ["shell", "dumpsys"]:
            return _result(args, "level: 77\n")
        if args[:2] == ["shell", "wm"]:
            return _result(args, "Physical size: 1080x2400\n")
        if args[:3] == ["shell", "pm", "list"]:
            return _result(args, "package:a\npackage:b\n")
        return _result(args)

    monkeypatch.setattr(gateway, "_run", fake_run)
    registered = gateway.register(endpoint, "My phone")
    assert registered["status"] == "ok"
    status = gateway.status()
    assert status["connected"] is True
    assert status["battery"] == 77
    assert status["packages"] == 2


def test_mutating_actions_require_confirmation(tmp_path):
    from aios_core.android_gateway import AndroidGateway

    gateway = AndroidGateway(tmp_path)
    assert gateway.open_app("com.example.app")["status"] == "need_confirm"
    assert gateway.tap(10, 20)["status"] == "need_confirm"
    assert gateway.key("KEYCODE_HOME")["status"] == "need_confirm"
