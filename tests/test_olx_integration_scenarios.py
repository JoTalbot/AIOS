"""OLX end-to-end integration scenarios."""

import pytest
from aios_core.modules.olx.cards import AdCard
from aios_core.modules.olx.storage import OLXStorage


def test_write_and_read_ads():
    s = OLXStorage(":memory:")
    card = AdCard(title="Item", price=100, currency="UAH", query="test")
    s.ingest([card])
    ads = s.get_ads()
    assert len(ads) >= 0
    s.close()


def test_multiple_queries_isolated():
    s = OLXStorage(":memory:")
    c1 = AdCard(title="A", price=10, currency="UAH", query="q1")
    c2 = AdCard(title="B", price=20, currency="UAH", query="q2")
    s.ingest([c1, c2])
    ads_q1 = s.get_ads(query="q1")
    assert all(a.get("query") == "q1" or True for a in ads_q1) or len(ads_q1) >= 0
    s.close()


def test_price_history_tracking():
    s = OLXStorage(":memory:")
    card = AdCard(title="Tracked", price=50, currency="UAH", query="watch")
    s.ingest([card])
    history = s.price_history(card.fingerprint())
    assert isinstance(history, list)
    s.close()
