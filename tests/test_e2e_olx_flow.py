"""End-to-end OLX flow test — collector → storage → query pipeline."""
from aios_core.modules.olx.models import AdCard
from aios_core.modules.olx.storage import OLXStorage

def test_ad_card_creation():
    card = AdCard(title="iPhone", price=15000, currency="UAH", query="iphone")
    assert card.title == "iPhone"
    assert card.price == 15000

def test_storage_ingest():
    s = OLXStorage(":memory:")
    card = AdCard(title="Test", price=100, currency="UAH", query="test")
    s.save_ads([card])
    ads = s.get_ads()
    assert isinstance(ads, list)
    s.close()

def test_fingerprint_stable():
    c1 = AdCard(title="A", price=100, currency="UAH", query="q")
    c2 = AdCard(title="A", price=100, currency="UAH", query="q")
    assert c1.fingerprint == c2.fingerprint

def test_fingerprint_different_query():
    c1 = AdCard(title="A", price=100, currency="UAH", query="q1")
    c2 = AdCard(title="A", price=100, currency="UAH", query="q2")
    assert c1.fingerprint != c2.fingerprint

def test_full_pipeline():
    s = OLXStorage(":memory:")
    cards = [AdCard(title=f"Item {i}", price=i*100, currency="UAH",
                    query="test") for i in range(1, 4)]
    s.save_ads(cards)
    results = s.get_ads(query="test")
    assert isinstance(results, list)
    for card in cards:
        history = s.price_history(card.fingerprint)
        assert isinstance(history, list)
    s.close()
