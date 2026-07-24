"""Tests for aios_core/privacy_guard.py"""
from __future__ import annotations
import pytest
from aios_core.privacy_guard import PrivacyGuard
from aios_core.storage import Database


@pytest.fixture()
def db(tmp_path):
    db = Database(db_path=str(tmp_path / "test.db"))
    yield db
    db.close()


@pytest.fixture()
def guard(db):
    return PrivacyGuard(db)


class TestPrivacyGuard:
    def test_create(self, guard):
        assert guard is not None

    def test_can_access(self, guard):
        result = guard.can_access(agent_id="u1", memory_category="docs", action="read")
        assert isinstance(result, (bool, dict))

    def test_can_share(self, guard):
        result = guard.can_share(data_classification="personal", target="external")
        assert isinstance(result, (bool, dict))

    def test_check_request(self, guard):
        result = guard.check_request(request={"user": "u1", "action": "read", "resource": "data"})
        assert isinstance(result, (bool, dict))

    def test_add_rule(self, guard):
        guard.add_rule(rule={"name": "no_share", "resource": "pii", "action": "share", "effect": "deny"})

    def test_classify(self, guard):
        result = guard.classify(data="user email: test@example.com")
        assert isinstance(result, (str, dict))

    def test_get_access_log(self, guard):
        log = guard.get_access_log()
        assert isinstance(log, list)

    def test_stats(self, guard):
        s = guard.stats()
        assert isinstance(s, dict)
