"""Telegram phone audit rendering never exposes workflow payloads."""
from __future__ import annotations


class API:
    def __init__(self):
        self.messages = []

    def send_message(self, *args, **kwargs):
        self.messages.append((args, kwargs))


def test_phone_audit_intent_renders_metadata_only(monkeypatch, tmp_path):
    import run_telegram_bot as bot
    from aios_core.android_audit import PhoneActionAudit

    PhoneActionAudit(tmp_path).record("easyway_route", "staged", package="com.eway")
    monkeypatch.setattr(bot, "PROJECT_ROOT", tmp_path)
    api = API()
    assert bot._handle_phone_audit_intent(api, 9001, "журнал телефона")
    text = str(api.messages[-1][0][1])
    assert "Черновик EasyWay" in text
    assert "координат" in text
    assert "секрет" not in text
