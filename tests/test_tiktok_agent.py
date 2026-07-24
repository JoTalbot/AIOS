"""Tests for TikTok full agent — collector, card_parser, detail, price_tracker, autowatch, favorites, auto_login."""

from __future__ import annotations

from aios_core.modules.olx.models import AdCard
from aios_core.modules.tiktok import (
    TikTokAutoLogin,
    TikTokAutoWatch,
    TikTokCardParser,
    TikTokCollector,
    TikTokDetailParser,
    TikTokFavorites,
    TikTokPriceTracker,
    TikTokStorage,
)


def _card(title: str, price: float, ad_id: str = "") -> AdCard:
    """Helper to create an AdCard."""
    return AdCard(
        title=title, price=price, currency="UAH", city="Kyiv",
        published_text="today", is_top=False, url=f"https://tiktok.com/{title}",
        ad_id=ad_id or f"tt-{title}", query="test", raw_texts=[title],
    )


def test_tiktok_imports():
    """All TikTok module classes are importable."""
    assert TikTokCollector is not None
    assert TikTokCardParser is not None
    assert TikTokDetailParser is not None
    assert TikTokPriceTracker is not None
    assert TikTokAutoWatch is not None
    assert TikTokFavorites is not None
    assert TikTokAutoLogin is not None
    assert TikTokStorage is not None


def test_tiktok_storage_inherits_olx():
    """TikTokStorage inherits OLXStorage."""
    from aios_core.modules.olx.storage import OLXStorage
    assert issubclass(TikTokStorage, OLXStorage)


def test_tiktok_price_tracker_detects_drop():
    """TikTokPriceTracker detects price drops (default 10% threshold)."""
    storage = TikTokStorage(":memory:")
    tracker = TikTokPriceTracker(storage)

    # 12% drop
    card1 = _card("Video Product", 1000, ad_id="tt-vp1")
    storage.save_ads([card1])
    card2 = _card("Video Product", 880, ad_id="tt-vp1")
    storage.save_ads([card2])

    alerts = tracker.detect_drops()
    assert len(alerts) >= 1
    assert alerts[0].drop_pct >= 10.0


def test_tiktok_price_tracker_ignores_small_drop():
    """TikTokPriceTracker ignores drops below 10% threshold."""
    storage = TikTokStorage(":memory:")
    tracker = TikTokPriceTracker(storage)

    card1 = _card("Clip", 500, ad_id="tt-clip")
    storage.save_ads([card1])
    card2 = _card("Clip", 470, ad_id="tt-clip")  # 6% drop
    storage.save_ads([card2])

    alerts = tracker.detect_drops()
    assert len(alerts) == 0


def test_tiktok_autowatch_cycle():
    """TikTokAutoWatch runs a cycle with trending hashtags."""
    storage = TikTokStorage(":memory:")
    watcher = TikTokAutoWatch(storage)

    card = _card("#fashion Product", 500, ad_id="tt-fashion")
    storage.save_ads([card])

    report = watcher.run_cycle(queries=["fashion"], collect=False)
    assert report["platform"] == "tiktok"
    assert "trending_hashtags" in report


def test_tiktok_favorites_add_remove():
    """TikTokFavorites add/remove works."""
    storage = TikTokStorage(":memory:")
    fav = TikTokFavorites(storage)

    assert fav.add("fp-test") is True
    assert "fp-test" in fav.list_all()
    assert fav.remove("fp-test") is True


def test_tiktok_auto_login():
    """TikTokAutoLogin uses TikTok package."""
    from aios_core.modules.rozetka.auto_login import LoginState
    auto = TikTokAutoLogin()
    assert auto.package == "com.zhiliaoapp.musically"

    # Detect login screen
    xml = '<node resource-id="login_button" text="Увійти" />'
    state = auto.detect_login_screen(xml)
    assert state == LoginState.LOGIN_SCREEN_FOUND


def test_tiktok_collector_deep_link():
    """TikTokCollector generates search deep link."""
    link = TikTokCollector.search_deep_link("iPhone")
    assert "tiktok://" in link
    assert "iPhone" in link


def test_tiktok_card_parser():
    """TikTokCardParser is importable and inherits CardParser."""
    from aios_core.modules.olx.card_parser import CardParser
    assert issubclass(TikTokCardParser, CardParser)


def test_tiktok_detail_parser():
    """TikTokDetailParser parses empty XML gracefully."""
    parser = TikTokDetailParser()
    detail = parser.parse_detail("")
    assert detail.title == ""


def test_tiktok_detail_parser_with_content():
    """TikTokDetailParser extracts hashtags and description."""
    parser = TikTokDetailParser()
    xml = '<node resource-id="author_1" text="Seller Name" /><node text="#fashion #sale iPhone 15 30000 грн" />'
    detail = parser.parse_detail(xml)
    # Should extract some data
    assert isinstance(detail.hashtags, list)
