"""Тесты оценки состояния операций без реальных systemd-вызовов."""
from __future__ import annotations


def test_collect_marks_failed_service_as_issue(monkeypatch, tmp_path):
    import run_ops_health as health

    monkeypatch.setattr(health, "ROOT", tmp_path)
    monkeypatch.setattr(health, "SERVICES", ("ok.service", "bad.service"))
    monkeypatch.setattr(health, "_backup_age_hours", lambda: 1.0)
    monkeypatch.setattr(health, "_mode", lambda _path: 0o600)
    report = health.collect(service_probe=lambda name: name == "ok.service")
    assert report["status"] == "degraded"
    assert "service:bad.service" in report["issues"]


def test_alert_state_deduplicates_unchanged_issues(monkeypatch, tmp_path):
    import run_ops_health as health

    monkeypatch.setattr(health, "STATE", tmp_path / "state.json")
    sent = []
    monkeypatch.setattr(health, "_notify", lambda text: sent.append(text))
    report = {"checked_at": "now", "issues": ["service:bad"], "warnings": []}
    first = health.alert_if_changed(report)
    second = health.alert_if_changed(report)
    assert first["created"] == ["service:bad"]
    assert second["created"] == []
    assert len(sent) == 1
