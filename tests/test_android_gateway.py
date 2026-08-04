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


def test_connect_replaces_stale_offline_endpoint(tmp_path, monkeypatch):
    from aios_core.android_gateway import AndroidGateway

    endpoint = "10.203.0.2:37081"
    gateway = AndroidGateway(tmp_path)
    gateway.data_dir.mkdir(parents=True)
    gateway.config_path.write_text('{"serial": "' + endpoint + '"}', encoding="utf-8")
    calls = []

    def fake_run(args, timeout=30, serial=None):
        calls.append((args, serial))
        if args[:2] == ["devices", "-l"]:
            return _result(args, f"List of devices attached\n{endpoint}\toffline\n")
        if args[0] == "connect":
            return _result(args, f"connected to {endpoint}\n")
        return _result(args)

    monkeypatch.setattr(gateway, "_run", fake_run)
    result = gateway.connect()
    assert result["status"] == "ok"
    assert result["previous_state"] == "offline"
    assert any(args == ["disconnect", endpoint] and serial == "" for args, serial in calls)
    assert any(args == ["connect", endpoint] and serial == "" for args, serial in calls)


def test_mutating_actions_require_confirmation(tmp_path):
    from aios_core.android_gateway import AndroidGateway

    gateway = AndroidGateway(tmp_path)
    assert gateway.open_app("com.example.app")["status"] == "need_confirm"
    assert gateway.tap(10, 20)["status"] == "need_confirm"
    assert gateway.key("KEYCODE_HOME")["status"] == "need_confirm"
    assert gateway.set_clipboard("text")["status"] == "need_confirm"
    assert gateway.tap_ui("Search")["status"] == "need_confirm"


def test_work_profiles_detect_installed_apps(tmp_path, monkeypatch):
    from aios_core.android_gateway import AndroidGateway

    gateway = AndroidGateway(tmp_path)
    monkeypatch.setattr(gateway, "apps", lambda limit=2000: {
        "status": "ok", "apps": ["com.whatsapp", "ua.com.abank", "ua.com.uklontaxi", "com.iMe.android"],
    })
    profiles = {p["id"]: p for p in gateway.app_profiles()["profiles"]}
    assert profiles["whatsapp"]["available"] is True
    assert profiles["abank"]["available"] is True
    assert profiles["privat24"]["available"] is False
    assert profiles["easyway"]["available"] is False


def test_easyway_profile_is_detected_after_install(tmp_path, monkeypatch):
    from aios_core.android_gateway import AndroidGateway

    gateway = AndroidGateway(tmp_path)
    monkeypatch.setattr(gateway, "apps", lambda limit=2000: {
        "status": "ok", "apps": ["com.eway"],
    })
    profiles = {p["id"]: p for p in gateway.app_profiles()["profiles"]}
    assert profiles["easyway"]["available"] is True
    assert profiles["easyway"]["installed"] == ["com.eway"]


def test_open_app_confirms_foreground_after_adb_timeout(tmp_path, monkeypatch):
    from aios_core.android_gateway import AndroidGateway

    gateway = AndroidGateway(tmp_path)
    monkeypatch.setattr(gateway, "status", lambda: {"connected": True})
    monkeypatch.setattr(gateway, "_run", lambda *args, **kwargs: _result(args, returncode=124, stderr="timeout"))
    monkeypatch.setattr(gateway, "_companion_request", lambda *args, **kwargs: {
        "status": "ok", "package": "com.eway", "nodes": [],
    })
    monkeypatch.setattr("aios_core.android_gateway.time.sleep", lambda _: None)

    result = gateway.open_app("com.eway", confirm=True)
    assert result["status"] == "ok"
    assert "Companion" in result["message"]

    monkeypatch.setattr(gateway, "_run", lambda *args, **kwargs: _result(args, returncode=1, stderr="monkey ended"))
    result = gateway.open_app("com.eway", confirm=True)
    assert result["status"] == "ok"


def test_capture_status_never_starts_camera_or_microphone(tmp_path, monkeypatch):
    from aios_core.android_gateway import AndroidGateway

    gateway = AndroidGateway(tmp_path)
    monkeypatch.setattr(gateway, "_companion_request", lambda path, timeout=12: {
        "status": "ok", "camera_permission": True, "microphone_permission": False,
        "camera_capture_enabled": False, "microphone_capture_enabled": False, "background_capture": False,
    })
    result = gateway.capture_status()
    assert result["camera_capture_enabled"] is False
    assert result["microphone_capture_enabled"] is False
    assert result["background_capture"] is False


def test_location_status_never_requires_confirmation_or_coordinates(tmp_path, monkeypatch):
    from aios_core.android_gateway import AndroidGateway

    gateway = AndroidGateway(tmp_path)
    monkeypatch.setattr(gateway, "_companion_request", lambda path, timeout=12: {
        "status": "ok", "permission": True, "gps_enabled": False,
        "network_enabled": True, "ready": True,
    })
    result = gateway.location_status()
    assert result["ready"] is True
    assert "latitude" not in result
    assert "longitude" not in result


def test_default_ui_snapshot_removes_screen_text(tmp_path, monkeypatch):
    from aios_core.android_gateway import AndroidGateway

    gateway = AndroidGateway(tmp_path)
    monkeypatch.setattr(gateway, "_companion_request", lambda *args, **kwargs: {
        "status": "ok", "package": "com.whatsapp", "nodes": [{
            "text": "private message", "description": "private description",
            "resource": "id/send", "clickable": True, "editable": False,
            "bounds": [1, 2, 30, 40],
        }],
    })
    safe = gateway.ui_snapshot(confirm=True)
    full = gateway.ui_snapshot(confirm=True, include_text=True)
    assert safe["package"] == "com.whatsapp"
    assert "text" not in safe["nodes"][0]
    assert "description" not in safe["nodes"][0]
    assert full["nodes"][0]["text"] == "private message"


def test_open_app_uses_resolved_activity_before_monkey(tmp_path, monkeypatch):
    from aios_core.android_gateway import AndroidGateway

    gateway = AndroidGateway(tmp_path)
    calls = []
    monkeypatch.setattr(gateway, "status", lambda: {"connected": True})

    def fake_run(args, timeout=30, serial=None):
        calls.append(args)
        if args[:4] == ["shell", "cmd", "package", "resolve-activity"]:
            return _result(args, "com.eway/.android.app.MainActivity\n")
        if args[:3] == ["shell", "am", "start"]:
            return _result(args, "Starting: Intent\n")
        return _result(args, returncode=1)

    monkeypatch.setattr(gateway, "_run", fake_run)
    result = gateway.open_app("com.eway", confirm=True)
    assert result["status"] == "ok"
    assert any(args[:3] == ["shell", "am", "start"] for args in calls)
    assert not any(args[:2] == ["shell", "monkey"] for args in calls)
