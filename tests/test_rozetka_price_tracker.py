"""Tests for Rozetka.ua price tracker — detect price drops and track products."""

from __future__ import annotations

from aios_core.modules.rozetka.storage import RozetkaStorage
from aios_core.modules.rozetka.price_tracker import RozetkaPriceTracker, PriceDropAlert
from aios_core.modules.olx.models import AdCard


def _card(title: str, price: float, url: str = "", ad_id: str = "") -> AdCard:
    """Helper to create an AdCard for testing with stable fingerprint via ad_id."""
    return AdCard(
        title=title,
        price=price,
        currency="UAH",
        city="Kyiv",
        published_text="today",
        is_top=False,
        url=url or f"https://rozetka.ua/{title}",
        ad_id=ad_id or f"r-{title}",
        query="test",
        raw_texts=[title],
    )


def test_price_tracker_no_drops_on_stable_price():
    """No alerts when prices remain stable."""
    storage = RozetkaStorage(":memory:")
    tracker = RozetkaPriceTracker(storage, min_drop_pct=5.0)

    card = _card("iPhone 15", 29999.0)
    storage.save_ads([card])
    storage.save_ads([card])

    alerts = tracker.detect_drops()
    assert len(alerts) == 0


def test_price_tracker_detects_drop():
    """Alert when price drops by ≥ min_drop_pct."""
    storage = RozetkaStorage(":memory:")
    tracker = RozetkaPriceTracker(storage, min_drop_pct=5.0)

    card1 = _card("iPhone 15", 30000.0, ad_id="r-iphone15")
    storage.save_ads([card1])

    card2 = _card("iPhone 15", 28000.0, ad_id="r-iphone15")
    storage.save_ads([card2])

    alerts = tracker.detect_drops()
    assert len(alerts) >= 1
    assert alerts[0].old_price == 30000.0
    assert alerts[0].new_price == 28000.0
    assert alerts[0].drop_pct >= 5.0


def test_price_tracker_ignores_small_drop():
    """No alert when price drop is below min_drop_pct."""
    storage = RozetkaStorage(":memory:")
    tracker = RozetkaPriceTracker(storage, min_drop_pct=10.0)

    card1 = _card("MacBook", 50000.0, ad_id="r-macbook")
    storage.save_ads([card1])

    card2 = _card("MacBook", 48000.0, ad_id="r-macbook")
    storage.save_ads([card2])

    alerts = tracker.detect_drops()
    assert len(alerts) == 0


def test_price_tracker_track_product():
    """track_product returns stats for a specific product."""
    storage = RozetkaStorage(":memory:")
    tracker = RozetkaPriceTracker(storage)

    card = _card("iPhone 15", 29999.0, ad_id="r-iphone15-track")
    storage.save_ads([card])
    storage.save_ads([card])

    stats = tracker.track_product(card.fingerprint)
    assert stats["fingerprint"] == card.fingerprint
    assert stats["current_price"] == 29999.0
    assert stats["min_price"] == 29999.0
    assert stats["max_price"] == 29999.0
    assert stats["price_count"] >= 1


def test_price_tracker_track_product_empty():
    """track_product returns empty stats for unknown fingerprint."""
    storage = RozetkaStorage(":memory:")
    tracker = RozetkaPriceTracker(storage)

    stats = tracker.track_product("nonexistent")
    assert stats["fingerprint"] == "nonexistent"
    assert stats["price_count"] == 0


def test_price_drop_alert_to_dict():
    """PriceDropAlert serializes to dict correctly."""
    alert = PriceDropAlert(
        fingerprint="fp-test",
        title="Test Product",
        old_price=1000.0,
        new_price=800.0,
        url="https://rozetka.ua/test",
        drop_pct=20.0,
        seen_at="2026-01-01T00:00:00+00:00",
    )
    d = alert.to_dict()
    assert d["fingerprint"] == "fp-test"
    assert d["old_price"] == 1000.0
    assert d["new_price"] == 800.0
    assert d["drop_pct"] == 20.0


def test_price_tracker_minimum_absolute_drop():
    """Drops below min_absolute_drop are ignored."""
    storage = RozetkaStorage(":memory:")
    tracker = RozetkaPriceTracker(storage, min_drop_pct=1.0, min_absolute_drop=100.0)

    card1 = _card("Plug", 10.0, ad_id="r-plug")
    storage.save_ads([card1])
    card2 = _card("Plug", 9.5, ad_id="r-plug")
    storage.save_ads([card2])

    alerts = tracker.detect_drops()
    assert len(alerts) == 0
