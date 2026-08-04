"""Tests for a daily, metadata-only phone control digest."""
from __future__ import annotations


def _snapshot():
    return {
        "status": "ok", "issues": [],
        "device": {"connected": True, "companion": True},
        "apps": [{"available": True, "calibrated": True}],
        "leads": {"pending": 2, "crm_open": 1, "crm_attention": 0, "crm_overdue": 0},
        "audit": {"count": 3},
        "timers": {"a": True, "b": True},
    }


def test_daily_digest_dry_run_does_not_send_or_store(monkeypatch, tmp_path):
    import run_phone_control_digest as digest

    monkeypatch.setattr(digest, "ROOT", tmp_path)
    monkeypatch.setattr(digest, "STATE", tmp_path / "state.json")

    class Center:
        def __init__(self, root): pass
        def snapshot(self): return _snapshot()

    sent = []
    monkeypatch.setattr(digest, "_send", lambda text: sent.append(text) or True)
    result = digest.check(dry_run=True, center_factory=Center)
    assert result["due"] is True
    assert result["sent"] is False
    assert "Ежедневная сводка" in result["text"]
    assert sent == []
    assert not digest.STATE.exists()


def test_daily_digest_sends_once_per_date(monkeypatch, tmp_path):
    import run_phone_control_digest as digest

    monkeypatch.setattr(digest, "ROOT", tmp_path)
    monkeypatch.setattr(digest, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(digest, "_today", lambda: "2026-08-04")

    class Center:
        def __init__(self, root): pass
        def snapshot(self): return _snapshot()

    sent = []
    monkeypatch.setattr(digest, "_send", lambda text: sent.append(text) or True)
    first = digest.check(center_factory=Center)
    second = digest.check(center_factory=Center)
    assert first["sent"] is True
    assert second["due"] is False
    assert len(sent) == 1
    assert "Переписки" in sent[0]


def test_bootstrap_marks_today_without_sending(monkeypatch, tmp_path):
    import run_phone_control_digest as digest

    monkeypatch.setattr(digest, "ROOT", tmp_path)
    monkeypatch.setattr(digest, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(digest, "_today", lambda: "2026-08-04")

    class Center:
        def __init__(self, root): pass
        def snapshot(self): return _snapshot()

    sent = []
    monkeypatch.setattr(digest, "_send", lambda text: sent.append(text) or True)
    result = digest.check(bootstrap=True, center_factory=Center)
    assert result["bootstrap"] is True
    assert result["sent"] is False
    assert sent == []
    assert '"last_date": "2026-08-04"' in digest.STATE.read_text()
