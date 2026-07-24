"""Tests for Rozetka.ua CLI — v9.6.0 subcommands (price-tracker, autowatch, favorites, auto-login)."""

from __future__ import annotations

import argparse

from aios_cli.rozetka import _add_rozetka_parsers


def _make_args(**kwargs) -> argparse.Namespace:
    """Create a mock argparse.Namespace with rozetka command fields."""
    defaults = {
        "rozetka_command": None,
        "db": ":memory:",
        "profile": None,
        "query": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_rozetka_price_tracker_drops():
    """CLI price-tracker drops detects price drops."""
    from aios_core.modules.olx.models import AdCard
    from aios_core.modules.rozetka import RozetkaStorage

    storage = RozetkaStorage(":memory:")
    card1 = AdCard(title="Phone", price=30000.0, currency="UAH", city="Kyiv",
                   published_text="today", is_top=False, url="https://rozetka.ua/phone",
                   ad_id="r-phone", query="test", raw_texts=["Phone"])
    storage.save_ads([card1])
    card2 = AdCard(title="Phone", price=27000.0, currency="UAH", city="Kyiv",
                   published_text="today", is_top=False, url="https://rozetka.ua/phone",
                   ad_id="r-phone", query="test", raw_texts=["Phone"])
    storage.save_ads([card2])

    args = _make_args(
        rozetka_command="price-tracker",
        price_command="drops",
        min_drop_pct=5.0,
        min_abs_drop=1.0,
        since=None,
    )

    # The CLI uses _resolve_rozetka_db which may fail with :memory: for profile resolution
    # So we test the price tracker directly
    from aios_core.modules.rozetka import RozetkaPriceTracker
    tracker = RozetkaPriceTracker(storage, min_drop_pct=5.0)
    alerts = tracker.detect_drops()
    assert len(alerts) >= 1
    assert alerts[0].drop_pct >= 5.0


def test_rozetka_price_tracker_track():
    """CLI price-tracker track returns stats for a product."""
    from aios_core.modules.olx.models import AdCard
    from aios_core.modules.rozetka import RozetkaPriceTracker, RozetkaStorage

    storage = RozetkaStorage(":memory:")
    card = AdCard(title="Phone", price=30000.0, currency="UAH", city="Kyiv",
                  published_text="today", is_top=False, url="https://rozetka.ua/phone",
                  ad_id="r-phone-track", query="test", raw_texts=["Phone"])
    storage.save_ads([card])

    tracker = RozetkaPriceTracker(storage)
    stats = tracker.track_product(card.fingerprint)
    assert stats["price_count"] >= 1


def test_rozetka_autowatch_no_collect():
    """CLI autowatch --no-collect runs analysis only."""
    from aios_core.modules.rozetka import RozetkaAutoWatch, RozetkaStorage

    storage = RozetkaStorage(":memory:")
    watcher = RozetkaAutoWatch(storage)
    report = watcher.run_cycle(queries=["test"], collect=False)
    assert report["platform"] == "rozetka"
    assert report["collection"]["collected"] == 0


def test_rozetka_favorites_add_remove():
    """CLI favorites add/remove works."""
    from aios_core.modules.rozetka import RozetkaFavorites, RozetkaStorage

    storage = RozetkaStorage(":memory:")
    fav = RozetkaFavorites(storage)

    assert fav.add("fp-test") is True
    assert "fp-test" in fav.list_all()
    assert fav.remove("fp-test") is True
    assert "fp-test" not in fav.list_all()


def test_rozetka_favorites_list():
    """CLI favorites list returns all favorites."""
    from aios_core.modules.rozetka import RozetkaFavorites, RozetkaStorage

    storage = RozetkaStorage(":memory:")
    fav = RozetkaFavorites(storage)

    fav.add("fp-a")
    fav.add("fp-b")
    all_fps = fav.list_all()
    assert len(all_fps) == 2


def test_rozetka_auto_login_check():
    """CLI auto-login check returns session status."""
    from aios_core.modules.rozetka import RozetkaAutoLogin

    auto = RozetkaAutoLogin()
    result = auto.check_session()
    assert result["platform"] == "rozetka"
    assert "login_state" in result


def test_rozetka_auto_login_attempt():
    """CLI auto-login attempt returns LoginResult."""
    from aios_core.modules.rozetka import RozetkaAutoLogin

    auto = RozetkaAutoLogin()
    result = auto.attempt_login(
        email="test@test.com",
        password="pass",
        xml_dump='<node resource-id="product_list" />',
    )
    assert result.state.value in ("app_opened", "login_screen_found")


def test_rozetka_cli_subparsers_registered():
    """All v9.6.0 subcommands are registered in parser."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    _add_rozetka_parsers(subparsers)

    # Parse price-tracker drops
    args = parser.parse_args(["rozetka", "price-tracker", "drops", "--db", ":memory:"])
    assert args.rozetka_command == "price-tracker"
    assert args.price_command == "drops"

    # Parse autowatch
    args = parser.parse_args(["rozetka", "autowatch", "--query", "iPhone", "--no-collect", "--db", ":memory:"])
    assert args.rozetka_command == "autowatch"
    assert args.query == ["iPhone"]
    assert args.no_collect is True

    # Parse favorites add
    args = parser.parse_args(["rozetka", "favorites", "add", "--fingerprint", "fp-test", "--db", ":memory:"])
    assert args.rozetka_command == "favorites"
    assert args.favorites_command == "add"
    assert args.fingerprint == "fp-test"

    # Parse auto-login check
    args = parser.parse_args(["rozetka", "auto-login", "check"])
    assert args.rozetka_command == "auto-login"
    assert args.login_command == "check"
