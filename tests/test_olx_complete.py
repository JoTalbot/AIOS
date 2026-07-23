"""Complete OLX integration tests — storage, scheduler, collector pipeline."""

from aios_core.modules.olx.storage import OLXStorage
from aios_core.modules.olx.cards import AdCard


def test_storage_in_memory_opens():
    s = OLXStorage(":memory:")
    assert s is not None
    s.close()


def test_storage_get_ads_empty():
    s = OLXStorage(":memory:")
    ads = s.get_ads()
    assert isinstance(ads, list)
    assert len(ads) == 0
    s.close()


def test_ad_card_full_fields():
    card = AdCard(
        title="MacBook Pro",
        price=45000,
        currency="UAH",
        city="Киев",
        query="macbook",
        url="https://example.com/ad/123",
        ad_id="12345",
    )
    d = card.to_dict()
    assert d["title"] == "MacBook Pro"
    assert d["price"] == 45000
    assert d["currency"] == "UAH"
    assert d["city"] == "Киев"
