"""Tests for aios_core/marketplace.py"""
from __future__ import annotations
import pytest
from aios_core.marketplace import CapabilityMarketplace
from aios_core.storage import Database


@pytest.fixture()
def db(tmp_path):
    db = Database(db_path=str(tmp_path / "test.db"))
    yield db
    db.close()


@pytest.fixture()
def market(db):
    return CapabilityMarketplace(db)


class TestCapabilityMarketplace:
    def test_publish(self, market):
        result = market.publish(name="test_cap", description="A test capability")
        assert result is not None

    def test_search(self, market):
        market.publish(name="searchable", description="Find me")
        results = market.search(query="searchable")
        assert isinstance(results, list)

    def test_search_by_tag(self, market):
        market.publish(name="tagged", description="d", tags=["important"])
        results = market.search(tag="important")
        assert isinstance(results, list)

    def test_get(self, market):
        item = market.publish(name="get_me", description="d")
        iid = getattr(item, 'item_id', getattr(item, 'id', None))
        if iid:
            fetched = market.get(iid)
            assert fetched is not None

    def test_download(self, market):
        item = market.publish(name="dl", description="d")
        iid = getattr(item, 'item_id', getattr(item, 'id', None))
        if iid:
            result = market.download(iid)
            assert result is not None

    def test_stats(self, market):
        market.publish(name="a", description="d")
        s = market.stats()
        assert isinstance(s, dict)

    def test_to_dict(self, market):
        d = market.to_dict()
        assert isinstance(d, dict)
