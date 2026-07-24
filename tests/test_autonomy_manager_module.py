"""Tests for aios_core/autonomy_manager.py"""
from __future__ import annotations
import pytest
from aios_core.autonomy_manager import AutonomyManager
from aios_core.storage import Database


@pytest.fixture()
def db(tmp_path):
    db = Database(db_path=str(tmp_path / "test.db"))
    yield db
    db.close()


@pytest.fixture()
def manager(db):
    return AutonomyManager(db)


class TestAutonomyManager:
    def test_grant_autonomy(self, manager):
        result = manager.grant_autonomy(agent_id="agent1", level=1)
        assert isinstance(result, dict)

    def test_revoke_autonomy(self, manager):
        manager.grant_autonomy(agent_id="agent1", level=1)
        result = manager.revoke_autonomy(agent_id="agent1", reason="testing")
        assert isinstance(result, dict)

    def test_check_autonomy(self, manager):
        manager.grant_autonomy(agent_id="agent1", level=1)
        result = manager.check_autonomy(agent_id="agent1")
        assert isinstance(result, dict)

    def test_check_autonomy_unknown(self, manager):
        result = manager.check_autonomy(agent_id="unknown")
        assert isinstance(result, dict)

    def test_record_action(self, manager):
        manager.grant_autonomy(agent_id="agent1", level=1)
        manager.record_action(agent_id="agent1", success=True)

    def test_should_promote(self, manager):
        manager.grant_autonomy(agent_id="agent1", level=1)
        for _ in range(10):
            manager.record_action(agent_id="agent1", success=True)
        result = manager.should_promote(agent_id="agent1")
        assert isinstance(result, dict)

    def test_should_demote(self, manager):
        manager.grant_autonomy(agent_id="agent1", level=3)
        result = manager.should_demote(agent_id="agent1")
        assert isinstance(result, dict)

    def test_get_profile(self, manager):
        manager.grant_autonomy(agent_id="agent1", level=1)
        profile = manager.get_profile(agent_id="agent1")
        assert profile is not None

    def test_list_profiles(self, manager):
        manager.grant_autonomy(agent_id="a1", level=1)
        manager.grant_autonomy(agent_id="a2", level=2)
        profiles = manager.list_profiles()
        assert isinstance(profiles, list)
        assert len(profiles) >= 2

    def test_stats(self, manager):
        s = manager.stats()
        assert isinstance(s, dict)
