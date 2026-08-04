"""Safe bank monitoring never exposes balances or notification payloads."""
from __future__ import annotations

import json


class Gateway:
    def __init__(self, root): self.root = root
    def app_profiles(self):
        return {"profiles": [
            {"id": "abank", "available": True},
            {"id": "privat24", "available": True},
        ]}


def test_bank_monitor_counts_only_unread_events(tmp_path):
    from aios_core.android_bank_monitor import AndroidBankMonitor, format_telegram

    data = tmp_path / "data" / "android_gateway"
    data.mkdir(parents=True)
    (data / "notifications.json").write_text(json.dumps([
        {"package": "ua.com.abank", "read": False, "text": "secret 123456"},
        {"package": "ua.privatbank.ap24", "read": True, "text": "balance"},
    ]), encoding="utf-8")
    snapshot = AndroidBankMonitor(tmp_path, gateway_factory=Gateway).snapshot()
    banks = {row["id"]: row for row in snapshot["banks"]}
    assert banks["abank"]["unread_notifications"] == 1
    assert banks["privat24"]["unread_notifications"] == 0
    text = format_telegram(snapshot)
    assert "123456" not in text
    assert "secret" not in text
