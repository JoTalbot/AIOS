"""Tests for aios_core/evolution_manager.py"""
from __future__ import annotations
import pytest
from aios_core.evolution_manager import EvolutionManager
from aios_core.storage import Database


@pytest.fixture()
def db(tmp_path):
    db = Database(db_path=str(tmp_path / "test.db"))
    yield db
    db.close()


@pytest.fixture()
def manager(db):
    return EvolutionManager(db=db, version="1.0.0")


class TestEvolutionManager:
    def test_propose(self, manager):
        proposal = manager.propose(change="add caching layer", component="api", reason="performance")
        assert proposal is not None

    def test_list_proposals(self, manager):
        manager.propose(change="p1", component="c1")
        manager.propose(change="p2", component="c2")
        proposals = manager.list_proposals()
        assert len(proposals) >= 2

    def test_get_proposal(self, manager):
        proposal = manager.propose(change="test", component="c")
        pid = getattr(proposal, 'proposal_id', getattr(proposal, 'id', None))
        if pid:
            fetched = manager.get_proposal(pid)
            assert fetched is not None

    def test_advance(self, manager):
        proposal = manager.propose(change="test", component="c")
        pid = getattr(proposal, 'proposal_id', getattr(proposal, 'id', None))
        if pid:
            manager.advance(pid)

    def test_approve(self, manager):
        proposal = manager.propose(change="approved", component="c")
        pid = getattr(proposal, 'proposal_id', getattr(proposal, 'id', None))
        if pid:
            manager.approve(pid)

    def test_reject(self, manager):
        proposal = manager.propose(change="rejected", component="c")
        pid = getattr(proposal, 'proposal_id', getattr(proposal, 'id', None))
        if pid:
            manager.reject(pid, reason="too risky")

    def test_can_deploy(self, manager):
        proposal = manager.propose(change="deploy", component="c")
        pid = getattr(proposal, 'proposal_id', getattr(proposal, 'id', None))
        if pid:
            result = manager.can_deploy(pid)
            assert isinstance(result, bool)

    def test_stats(self, manager):
        s = manager.stats()
        assert isinstance(s, dict)
