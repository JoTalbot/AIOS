"""Tests for metadata-only Android messenger lead candidates."""
from __future__ import annotations

import json


def test_sync_keeps_notification_content_out_of_lead_queue(tmp_path):
    from aios_core.android_leads import AndroidLeadQueue

    data = tmp_path / "data" / "android_gateway"
    data.mkdir(parents=True)
    (data / "notifications.json").write_text(json.dumps([
        {
            "id": "wh-1", "package": "com.whatsapp", "app": "WhatsApp",
            "title": "Иван", "text": "секретный текст 123456", "collected_at": "2026-08-04T10:00:00+00:00",
        },
        {
            "id": "bank-1", "package": "ua.com.abank", "app": "A-Bank",
            "title": "bank", "text": "не импортировать", "collected_at": "2026-08-04T10:01:00+00:00",
        },
        {
            "id": "ime-1", "package": "com.iMe.android", "app": "iMe",
            "title": "Имя", "text": "личное", "collected_at": "2026-08-04T10:02:00+00:00",
        },
    ], ensure_ascii=False), encoding="utf-8")

    queue = AndroidLeadQueue(tmp_path)
    first = queue.sync()
    second = queue.sync()
    assert first["added"] == 2
    assert second["added"] == 0
    assert queue.summary()["pending"] == 2
    raw = (data / "lead_candidates.json").read_text(encoding="utf-8")
    assert "секретный текст" not in raw
    assert "123456" not in raw
    assert "Иван" not in raw
    rows = queue.list_pending()
    assert {row["source"] for row in rows} == {"WhatsApp", "iMe Messenger"}
    assert queue.review(rows[0]["id"])["status"] == "reviewed"
    assert queue.summary()["pending"] == 1
    assert (data / "lead_candidates.json").stat().st_mode & 0o777 == 0o600
