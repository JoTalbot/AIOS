"""Тесты Signal Desktop control без реального VNC и переписок."""
from __future__ import annotations

import json


def _word(text: str, x: int, y: int) -> dict:
    return {"text": text, "x0": x, "y0": y, "w": 60, "h": 18,
            "cx": x + 30, "cy": y + 9, "conf": 90.0}


def test_signal_read_marks_right_bubbles_as_mine(monkeypatch):
    import signal_control as sc

    monkeypatch.setattr(sc, "_activate", lambda: "42")
    monkeypatch.setattr(sc, "_find_phrase", lambda *args, **kwargs: (100, 100))
    monkeypatch.setattr(sc, "_click", lambda *args, **kwargs: None)
    monkeypatch.setattr(sc, "_shot", lambda name: f"/tmp/{name}.png")
    monkeypatch.setattr(sc.time, "sleep", lambda *_: None)
    calls = iter([
        [_word("Чат", 100, 100)],
        [_word("Входящее", 760, 400), _word("сообщение", 840, 400),
         _word("Моё", 1420, 450), _word("сообщение", 1500, 450)],
    ])
    monkeypatch.setattr(sc, "_ocr", lambda _path: next(calls))

    result = sc.read_chat("Чат")
    assert result["status"] == "ok"
    assert [m["mine"] for m in result["messages"]] == [False, True]


def test_signal_chats_groups_ocr_words_into_chat_rows(monkeypatch):
    import signal_control as sc

    monkeypatch.setattr(sc, "_activate", lambda: "42")
    monkeypatch.setattr(sc, "_shot", lambda name: f"/tmp/{name}.png")
    monkeypatch.setattr(sc, "_ocr", lambda _path: [
        _word("Рабочий", 100, 150), _word("чат", 180, 150),
        _word("Личный", 100, 240), _word("чат", 170, 240),
        _word("Search", 100, 80),  # верхняя панель — исключается
    ])
    result = sc.chats()
    assert result["status"] == "ok"
    assert [x["name"] for x in result["chats"]] == ["Рабочий чат", "Личный чат"]


def test_signal_platform_config_can_be_draft_only(tmp_path, monkeypatch):
    import run_platform_autoreply as autoreply

    config = tmp_path / "platform_autoreply.json"
    config.write_text(json.dumps({
        "enabled": True,
        "auto_send": True,
        "platforms": {"signal": {"enabled": True, "auto_send": False,
                                   "max_replies_per_run": 2, "allowed_chats": ["Рабочий"]}},
    }), encoding="utf-8")
    monkeypatch.setattr(autoreply, "CFG_PATH", config)

    signal = autoreply._load_cfg("signal")
    assert signal["auto_send"] is False
    assert autoreply._contact_allowed("signal", "Рабочий", signal) is True
    assert autoreply._contact_allowed("signal", "Личный", signal) is False


def test_signal_status_is_read_only(monkeypatch):
    import signal_control as sc

    monkeypatch.setattr(sc, "win_id", lambda: "777")
    result = sc.status()
    assert result["status"] == "ok"
    assert result["ready"] is True
