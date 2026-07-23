"""Additional smoke tests for OLX modules."""

from aios_core.modules.olx.cards import AdCard
from aios_core.modules.olx.promotion import AdImprover, Reposter


def test_ad_card_fingerprint():
    card1 = AdCard(title="Item A", price=100, currency="UAH", query="search")
    card2 = AdCard(title="Item A", price=100, currency="UAH", query="search")
    assert card1.fingerprint() == card2.fingerprint()


def test_ad_card_to_dict():
    card = AdCard(title="Test", price=50, currency="USD", query="q")
    d = card.to_dict()
    assert d["title"] == "Test"
    assert d["price"] == 50


def test_ad_improver_init():
    ai = AdImprover()
    assert ai is not None


def test_reposter_init():
    r = Reposter()
    assert r is not None
