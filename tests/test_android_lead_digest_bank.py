"""Bank task IDs join the metadata-only digest without payloads."""
from __future__ import annotations


def test_digest_alerts_new_bank_task_metadata(monkeypatch, tmp_path):
    import run_android_lead_digest as digest

    monkeypatch.setattr(digest, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(digest, "_queue_snapshot", lambda: ([], {"crm_open": 0, "crm_attention": 0, "crm_overdue": 0}))
    tasks = []
    monkeypatch.setattr(digest, "_bank_tasks", lambda: list(tasks))
    sent = []
    monkeypatch.setattr(digest, "_send", lambda text: sent.append(text) or True)
    digest.check(bootstrap=True)
    tasks.append({"id": "bank-1", "source": "A-Bank", "observed_at": "now"})
    report = digest.check(alert=True)
    assert report["bank_new"] == 1
    assert report["sent"] is True
    assert "банковских задач" in sent[0]
    assert "123456" not in sent[0]
