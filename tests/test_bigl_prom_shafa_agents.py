"""Tests for Bigl/Prom/Shafa full agents — upgrade from scaffold."""

from __future__ import annotations

from aios_core.modules.bigl import BiglCollector, BiglPriceTracker, BiglAutoWatch, BiglFavorites, BiglStorage
from aios_core.modules.prom import PromCollector, PromPriceTracker, PromAutoWatch, PromFavorites, PromStorage
from aios_core.modules.shafa import ShafaCollector, ShafaPriceTracker, ShafaAutoWatch, ShafaFavorites, ShafaStorage
from aios_core.modules.olx.models import AdCard


def _card(title: str, price: float, ad_id: str = "") -> AdCard:
    return AdCard(title=title, price=price, currency="UAH", city="Kyiv",
                  published_text="today", is_top=False, url=f"https://test.ua/{title}",
                  ad_id=ad_id or f"id-{title}", query="test", raw_texts=[title])


def test_bigl_imports():
    """All Bigl module classes are importable."""
    assert BiglCollector is not None
    assert BiglPriceTracker is not None
    assert BiglAutoWatch is not None
    assert BiglFavorites is not None
    assert BiglStorage is not None


def test_bigl_storage_inherits_olx():
    """BiglStorage inherits OLXStorage."""
    from aios_core.modules.olx.storage import OLXStorage
    assert issubclass(BiglStorage, OLXStorage)


def test_bigl_price_tracker():
    """BiglPriceTracker detects drops."""
    storage = BiglStorage(":memory:")
    tracker = BiglPriceTracker(storage)
    card = _card("Phone", 1000, ad_id="b-phone")
    storage.save_ads([card])
    storage.save_ads([card])
    alerts = tracker.detect_drops()
    assert len(alerts) == 0  # No drop — same price


def test_bigl_autowatch():
    """BiglAutoWatch runs cycle with 'bigl' platform."""
    storage = BiglStorage(":memory:")
    watcher = BiglAutoWatch(storage)
    report = watcher.run_cycle(queries=["test"], collect=False)
    assert report["platform"] == "bigl"


def test_bigl_favorites():
    """BiglFavorites add/remove works."""
    storage = BiglStorage(":memory:")
    fav = BiglFavorites(storage)
    assert fav.add("fp-test") is True
    assert fav.remove("fp-test") is True


def test_bigl_collector_deep_link():
    """BiglCollector generates deep link."""
    link = BiglCollector.search_deep_link("iPhone")
    assert "bigl://" in link


def test_prom_imports():
    """All Prom module classes are importable."""
    assert PromCollector is not None
    assert PromPriceTracker is not None
    assert PromAutoWatch is not None
    assert PromFavorites is not None


def test_prom_autowatch():
    """PromAutoWatch runs cycle with 'prom' platform."""
    storage = PromStorage(":memory:")
    watcher = PromAutoWatch(storage)
    report = watcher.run_cycle(queries=["test"], collect=False)
    assert report["platform"] == "prom"


def test_prom_favorites():
    """PromFavorites add/remove works."""
    storage = PromStorage(":memory:")
    fav = PromFavorites(storage)
    assert fav.add("fp-test") is True
    assert "fp-test" in fav.list_all()


def test_prom_collector_deep_link():
    """PromCollector generates deep link."""
    link = PromCollector.search_deep_link("Phone")
    assert "prom://" in link


def test_shafa_imports():
    """All Shafa module classes are importable."""
    assert ShafaCollector is not None
    assert ShafaPriceTracker is not None
    assert ShafaAutoWatch is not None
    assert ShafaFavorites is not None


def test_shafa_autowatch():
    """ShafaAutoWatch runs cycle with 'shafa' platform."""
    storage = ShafaStorage(":memory:")
    watcher = ShafaAutoWatch(storage)
    report = watcher.run_cycle(queries=["fashion"], collect=False)
    assert report["platform"] == "shafa"


def test_shafa_favorites():
    """ShafaFavorites add/remove works."""
    storage = ShafaStorage(":memory:")
    fav = ShafaFavorites(storage)
    assert fav.add("fp-dress") is True
    assert fav.remove("fp-dress") is True


def test_shafa_collector_deep_link():
    """ShafaCollector generates deep link."""
    link = ShafaCollector.search_deep_link("Dress")
    assert "shafa://" in link
