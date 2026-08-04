"""Tests for the metadata-only Android action audit trail."""
from __future__ import annotations

import json


def test_phone_audit_keeps_only_safe_metadata(tmp_path):
    from aios_core.android_audit import PhoneActionAudit

    audit = PhoneActionAudit(tmp_path)
    audit.record("messenger_draft", "ready", package="com.whatsapp")
    event = audit.recent()[0]
    assert event["action"] == "messenger_draft"
    assert event["package"] == "com.whatsapp"
    raw = (tmp_path / "data" / "android_gateway" / "action_audit.json").read_text(encoding="utf-8")
    assert set(json.loads(raw)[0]) <= {"at", "action", "status", "package"}
    assert (tmp_path / "data" / "android_gateway" / "action_audit.json").stat().st_mode & 0o777 == 0o600
