"""Tests for Rozetka.ua AutoWatch cycle."""

from __future__ import annotations

from aios_core.modules.olx.models import AdCard
from aios_core.modules.rozetka.autowatch import RozetkaAutoWatch
from aios_core.modules.rozetka.price_tracker import RozetkaPriceTracker
from aios_core.modules.rozetka.storage import RozetkaStorage


def _card(title: str, price: float, ad_id: str = "") -> AdCard:
    """Helper to create an AdCard for testing."""
    return AdCard(
        title=title,
        price=price,
        currency="UAH",
        city="Kyiv",
        published_text="today",
        is_top=False,
        url=f"https://rozetka.ua/{title}",
        ad_id=ad_id or f"r-{title}",
        query="test",
        raw_texts=[title],
    )


def test_autowatch_run_cycle_no_collect():
    """AutoWatch cycle without collection just analyzes existing data."""
    storage = RozetkaStorage(":memory:")
    watcher = RozetkaAutoWatch(storage)

    report = watcher.run_cycle(queries=["iPhone"], collect=False)
    assert report["platform"] == "rozetka"
    assert "started_at" in report
    assert "completed_at" in report
    assert report["collection"]["collected"] == 0


def test_autowatch_detects_price_drops():
    """AutoWatch detects price drops during cycle."""
    storage = RozetkaStorage(":memory:")
    tracker = RozetkaPriceTracker(storage, min_drop_pct=5.0)
    watcher = RozetkaAutoWatch(storage, price_tracker=tracker)

    card1 = _card("iPhone 15", 30000.0, ad_id="r-iphone15")
    storage.save_ads([card1])
    card2 = _card("iPhone 15", 27000.0, ad_id="r-iphone15")
    storage.save_ads([card2])

    report = watcher.run_cycle(queries=["iPhone 15"], collect=False)
    assert len(report["price_drop_alerts"]) >= 1


def test_autowatch_no_drops_stable():
    """AutoWatch reports no drops for stable prices."""
    storage = RozetkaStorage(":memory:")
    watcher = RozetkaAutoWatch(storage)

    card = _card("iPad", 15000.0, ad_id="r-ipad")
    storage.save_ads([card])
    storage.save_ads([card])

    report = watcher.run_cycle(queries=["iPad"], collect=False)
    assert len(report["price_drop_alerts"]) == 0


def test_autowatch_stagnant_products():
    """AutoWatch detects stagnant products (not seen recently)."""
    storage = RozetkaStorage(":memory:")
    watcher = RozetkaAutoWatch(storage, min_age_days=0.0)

    card = _card("Old Phone", 5000.0, ad_id="r-old")
    storage.save_ads([card])

    report = watcher.run_cycle(queries=["test"], collect=False)
    assert isinstance(report["stagnant"], list)


def test_autowatch_favorite_alerts():
    """AutoWatch checks favorites for price drops."""
    storage = RozetkaStorage(":memory:")
    watcher = RozetkaAutoWatch(storage)

    card1 = _card("Watch", 5000.0, ad_id="r-watch")
    storage.save_ads([card1])
    card2 = _card("Watch", 4500.0, ad_id="r-watch")
    storage.save_ads([card2])

    # Add to favorites
    storage.favorite_add(card1.fingerprint)

    report = watcher.run_cycle(queries=["Watch"], collect=False)
    assert isinstance(report["favorite_alerts"], list)
    assert len(report["favorite_alerts"]) >= 1
