"""Metadata-only synchronization freshness status tests."""
from __future__ import annotations

import json


def test_sync_status_reports_files_without_payloads(tmp_path):
    from aios_core.phone_sync_status import PhoneSyncStatus

    data = tmp_path / "data" / "android_gateway"
    data.mkdir(parents=True)
    (data / "lead_sync_state.json").write_text(json.dumps({"checked_at": "2026-08-04T10:00:00+00:00", "secret": "not surfaced"}), encoding="utf-8")
    report = PhoneSyncStatus(tmp_path).snapshot()
    lead = next(item for item in report["sources"] if item["id"] == "lead_sync")
    assert lead["exists"] is True
    assert "secret" not in str(report)
