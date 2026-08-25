"""Тесты аудита OpenHands-контура: маскирование секретов и запись событий.

Без моков: реальный ``aios_core.audit_logger.AuditLogger`` (in-memory режим).
"""

import pytest

from aios_core.openhands.audit import MASK, OHAuditLogger, mask_secrets
from aios_core.openhands.models import AgentRole


class TestMaskSecrets:
    def test_sensitive_keys_masked(self):
        event = {
            "api_key": "sk-live-abcdef123456",
            "Authorization": "Bearer xyz",
            "nested": {"db_password": "hunter2", "note": "ok"},
        }
        masked = mask_secrets(event)
        assert masked["api_key"] == MASK
        assert masked["Authorization"] == MASK
        assert masked["nested"]["db_password"] == MASK
        assert masked["nested"]["note"] == "ok"

    def test_long_token_like_values_masked(self):
        masked = mask_secrets({"output": "key= ghp_a1b2c3d4e5f6a7b8c9d0e1f2 end"})
        assert "ghp_" not in masked["output"]
        assert MASK in masked["output"]

    def test_short_normal_strings_untouched(self):
        assert mask_secrets({"action": "commit", "files": ["a.py", "b.py"]}) == {
            "action": "commit",
            "files": ["a.py", "b.py"],
        }

    def test_lists_and_tuples(self):
        masked = mask_secrets({"items": [{"token": "x"}, "plain"]})
        assert masked["items"][0]["token"] == MASK
        assert masked["items"][1] == "plain"


class TestOHAuditLogger:
    @pytest.fixture
    def audit(self, tmp_path):
        from aios_core.audit_logger import AuditLogger

        # file_path в tmp: AuditLogger без db пишет best-effort JSONL рядом с cwd.
        return OHAuditLogger(AuditLogger(file_path=str(tmp_path / "audit.jsonl")))

    def test_log_transition(self, audit):
        event = audit.log_transition("t-1", AgentRole.ORCHESTRATOR, "pending", "planning")
        assert event["type"] == "openhands.transition"
        assert event["task_id"] == "t-1"
        assert event["agent"] == "orchestrator"
        assert event["src"] == "pending"
        assert event["dst"] == "planning"
        assert "id" in event and "timestamp" in event

    def test_log_decision_masks_secrets(self, audit):
        audit.log_decision(
            "t-2",
            AgentRole.SECURITY,
            "blocked",
            detail="leak suspected",
            api_token="super-secret-value-1234567890",
        )
        stored = audit.backend.query(event_type="openhands.decision")
        assert stored, "событие должно быть записано"
        assert stored[0]["api_token"] == MASK
        assert stored[0]["decision"] == "blocked"

    def test_role_accepts_plain_string(self, audit):
        event = audit.log("custom", "t-3", "security")
        assert event["agent"] == "security"
        assert event["type"] == "openhands.custom"
