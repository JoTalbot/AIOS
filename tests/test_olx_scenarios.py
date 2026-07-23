"""OLX scenario tests — end-to-end flows."""

from aios_core.modules.olx.cards import AdCard
from aios_core.modules.olx.competitive import CompetitorAnalyzer


def test_ad_card_fingerprint_stability():
    c1 = AdCard(title="iPhone 12", price=15000, currency="UAH", query="iphone")
    c2 = AdCard(title="iPhone 12", price=15000, currency="UAH", query="iphone")
    assert c1.fingerprint() == c2.fingerprint()


def test_ad_card_different_query():
    c1 = AdCard(title="iPhone 12", price=15000, currency="UAH", query="iphone")
    c2 = AdCard(title="iPhone 12", price=15000, currency="UAH", query="apple")
    assert c1.fingerprint() != c2.fingerprint()


def test_competitor_analyzer_init():
    ca = CompetitorAnalyzer()
    assert ca is not None
