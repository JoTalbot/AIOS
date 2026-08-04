"""Tests for rate-limited, metadata-only lead digest notifications."""
from __future__ import annotations


def test_bootstrap_suppresses_existing_lead_alerts(monkeypatch, tmp_path):
    import run_android_lead_digest as digest

    monkeypatch.setattr(digest, "STATE", tmp_path / "state.json")
    rows = [{"id": "a", "source": "iMe Messenger"}]
    monkeypatch.setattr(digest, "_queue_snapshot", lambda: (list(rows), {"crm_open": 0, "crm_attention": 0, "crm_overdue": 0}))
    sent = []
    monkeypatch.setattr(digest, "_send", lambda text: sent.append(text) or True)

    initial = digest.check(alert=True, bootstrap=True)
    assert initial["new"] == 1
    assert initial["sent"] is False
    again = digest.check(alert=True)
    assert again["new"] == 0
    assert sent == []


def test_digest_alerts_only_new_metadata_ids(monkeypatch, tmp_path):
    import run_android_lead_digest as digest

    monkeypatch.setattr(digest, "STATE", tmp_path / "state.json")
    rows = [{"id": "old", "source": "WhatsApp"}]
    monkeypatch.setattr(digest, "_queue_snapshot", lambda: (list(rows), {"crm_open": 0, "crm_attention": 0, "crm_overdue": 0}))
    sent = []
    monkeypatch.setattr(digest, "_send", lambda text: sent.append(text) or True)
    digest.check(bootstrap=True)
    rows.append({"id": "new", "source": "iMe Messenger"})
    report = digest.check(alert=True)
    assert report["new"] == 1
    assert report["by_source"] == {"iMe Messenger": 1}
    assert report["sent"] is True
    assert len(sent) == 1
    assert "new" not in sent[0]  # IDs are never rendered


def test_digest_alerts_when_followup_becomes_overdue(monkeypatch, tmp_path):
    import run_android_lead_digest as digest

    monkeypatch.setattr(digest, "STATE", tmp_path / "state.json")
    rows = []
    state = {"crm_open": 1, "crm_attention": 0, "crm_overdue": 0}
    monkeypatch.setattr(digest, "_queue_snapshot", lambda: (list(rows), dict(state)))
    sent = []
    monkeypatch.setattr(digest, "_send", lambda text: sent.append(text) or True)
    digest.check(bootstrap=True)
    state.update({"crm_attention": 1, "crm_overdue": 1})
    report = digest.check(alert=True)
    assert report["new"] == 0
    assert report["crm_overdue"] == 1
    assert report["sent"] is True
    assert len(sent) == 1
