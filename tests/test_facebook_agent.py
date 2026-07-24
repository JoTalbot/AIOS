"""Tests for Facebook Marketplace full agent — collector, card_parser, detail, price_tracker, autowatch, favorites, auto_login."""

from __future__ import annotations

from aios_core.modules.facebook import (
    FacebookAutoLogin,
    FacebookAutoWatch,
    FacebookCardParser,
    FacebookCollector,
    FacebookDetailParser,
    FacebookFavorites,
    FacebookPriceTracker,
    FacebookStorage,
)
from aios_core.modules.olx.models import AdCard


def _card(title: str, price: float, ad_id: str = "") -> AdCard:
    """Helper to create an AdCard."""
    return AdCard(
        title=title, price=price, currency="UAH", city="Kyiv",
        published_text="today", is_top=False, url=f"https://fb.com/{title}",
        ad_id=ad_id or f"fb-{title}", query="test", raw_texts=[title],
    )


def test_facebook_imports():
    """All Facebook module classes are importable."""
    assert FacebookCollector is not None
    assert FacebookCardParser is not None
    assert FacebookDetailParser is not None
    assert FacebookPriceTracker is not None
    assert FacebookAutoWatch is not None
    assert FacebookFavorites is not None
    assert FacebookAutoLogin is not None
    assert FacebookStorage is not None


def test_facebook_storage_inherits_olx():
    """FacebookStorage inherits OLXStorage."""
    from aios_core.modules.olx.storage import OLXStorage
    assert issubclass(FacebookStorage, OLXStorage)


def test_facebook_price_tracker_detects_drop():
    """FacebookPriceTracker detects price drops."""
    storage = FacebookStorage(":memory:")
    tracker = FacebookPriceTracker(storage)

    card1 = _card("Table", 5000, ad_id="fb-table")
    storage.save_ads([card1])
    card2 = _card("Table", 4500, ad_id="fb-table")
    storage.save_ads([card2])

    alerts = tracker.detect_drops()
    assert len(alerts) >= 1


def test_facebook_autowatch_cycle():
    """FacebookAutoWatch runs a cycle."""
    storage = FacebookStorage(":memory:")
    watcher = FacebookAutoWatch(storage)

    report = watcher.run_cycle(queries=["furniture"], collect=False)
    assert report["platform"] == "facebook"


def test_facebook_favorites():
    """FacebookFavorites add/remove works."""
    storage = FacebookStorage(":memory:")
    fav = FacebookFavorites(storage)

    assert fav.add("fp-fb-test") is True
    assert "fp-fb-test" in fav.list_all()
    assert fav.remove("fp-fb-test") is True


def test_facebook_auto_login():
    """FacebookAutoLogin uses Facebook package."""
    from aios_core.modules.rozetka.auto_login import LoginState
    auto = FacebookAutoLogin()
    assert auto.package == "com.facebook.katana"

    xml = '<node resource-id="login_button" />'
    state = auto.detect_login_screen(xml)
    assert state == LoginState.LOGIN_SCREEN_FOUND


def test_facebook_collector_deep_link():
    """FacebookCollector generates marketplace deep link."""
    link = FacebookCollector.search_deep_link("iPhone")
    assert "fb://marketplace" in link
    assert "iPhone" in link


def test_facebook_detail_parser_empty():
    """FacebookDetailParser handles empty XML."""
    parser = FacebookDetailParser()
    result = parser.parse_detail("")
    assert result == {}


def test_facebook_detail_parser_with_content():
    """FacebookDetailParser extracts data from XML."""
    parser = FacebookDetailParser()
    xml = '<node text="Beautiful table 5000 грн" /><node resource-id="seller_1" text="Seller" />'
    result = parser.parse_detail(xml)
    assert "description" in result
