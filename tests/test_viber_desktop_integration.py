"""Тесты безопасного desktop-контура Viber без реального VNC/сообщений."""
from __future__ import annotations

import json
from pathlib import Path


def _word(text: str, x: int, y: int) -> dict:
    return {"text": text, "x0": x, "y0": y, "w": 60, "h": 18,
            "cx": x + 30, "cy": y + 9, "conf": 90.0}


def test_viber_read_marks_right_bubbles_as_mine(monkeypatch):
    import viber_control as vc

    monkeypatch.setattr(vc, "_activate", lambda: "42")
    monkeypatch.setattr(vc, "_find_phrase", lambda *args, **kwargs: (100, 100))
    monkeypatch.setattr(vc, "_click", lambda *args, **kwargs: None)
    monkeypatch.setattr(vc, "_shot", lambda name: f"/tmp/{name}.png")
    monkeypatch.setattr(vc.time, "sleep", lambda *_: None)
    calls = iter([
        [_word("Чат", 100, 100)],
        [_word("Входящее", 760, 400), _word("сообщение", 840, 400),
         _word("Моё", 1420, 450), _word("сообщение", 1500, 450)],
    ])
    monkeypatch.setattr(vc, "_ocr", lambda _path: next(calls))

    result = vc.read_chat("Чат")
    assert result["status"] == "ok"
    assert [m["mine"] for m in result["messages"]] == [False, True]


def test_viber_platform_config_can_be_draft_only(tmp_path, monkeypatch):
    import run_platform_autoreply as autoreply

    config = tmp_path / "platform_autoreply.json"
    config.write_text(json.dumps({
        "enabled": True,
        "auto_send": True,
        "max_replies_per_run": 3,
        "platforms": {"viber": {"enabled": True, "auto_send": False, "max_replies_per_run": 2}},
    }), encoding="utf-8")
    monkeypatch.setattr(autoreply, "CFG_PATH", config)

    assert autoreply._load_cfg("instagram")["auto_send"] is True
    viber = autoreply._load_cfg("viber")
    assert viber["enabled"] is True
    assert viber["auto_send"] is False
    assert viber["max_replies_per_run"] == 2


def test_viber_status_is_read_only(monkeypatch):
    import viber_control as vc

    monkeypatch.setattr(vc, "win_id", lambda: "777")
    result = vc.status()
    assert result["status"] == "ok"
    assert result["ready"] is True
