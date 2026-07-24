"""Tests for Rozetka.ua favorites module."""

from __future__ import annotations

from aios_core.modules.olx.models import AdCard
from aios_core.modules.rozetka.favorites import RozetkaFavorites
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


def test_favorites_add():
    """Add a product to favorites."""
    storage = RozetkaStorage(":memory:")
    fav = RozetkaFavorites(storage)

    result = fav.add("fp-iphone")
    assert result is True
    assert "fp-iphone" in fav.list_all()


def test_favorites_add_duplicate():
    """Adding same fingerprint twice returns False (already favorite)."""
    storage = RozetkaStorage(":memory:")
    fav = RozetkaFavorites(storage)

    fav.add("fp-iphone")
    result = fav.add("fp-iphone")
    assert result is False


def test_favorites_remove():
    """Remove a product from favorites."""
    storage = RozetkaStorage(":memory:")
    fav = RozetkaFavorites(storage)

    fav.add("fp-iphone")
    result = fav.remove("fp-iphone")
    assert result is True
    assert "fp-iphone" not in fav.list_all()


def test_favorites_remove_nonexistent():
    """Removing nonexistent fingerprint returns False."""
    storage = RozetkaStorage(":memory:")
    fav = RozetkaFavorites(storage)

    result = fav.remove("nonexistent")
    assert result is False


def test_favorites_list_with_details():
    """List favorites with product details."""
    storage = RozetkaStorage(":memory:")
    tracker = RozetkaPriceTracker(storage)
    fav = RozetkaFavorites(storage, price_tracker=tracker)

    card = _card("iPhone 15", 29999.0, ad_id="r-iphone15")
    storage.save_ads([card])
    fav.add(card.fingerprint)

    details = fav.list_with_details()
    assert len(details) >= 1
    assert details[0]["fingerprint"] == card.fingerprint
    assert details[0]["title"] == "iPhone 15"
    assert details[0]["price"] == 29999.0


def test_favorites_check_drops():
    """Check favorites for price drops."""
    storage = RozetkaStorage(":memory:")
    tracker = RozetkaPriceTracker(storage, min_drop_pct=5.0)
    fav = RozetkaFavorites(storage, price_tracker=tracker, min_drop_pct=5.0)

    card1 = _card("Watch", 5000.0, ad_id="r-watch")
    storage.save_ads([card1])
    card2 = _card("Watch", 4500.0, ad_id="r-watch")
    storage.save_ads([card2])

    fav.add(card1.fingerprint)

    drops = fav.check_drops()
    assert len(drops) >= 1
    assert drops[0]["fingerprint"] == card1.fingerprint
    assert drops[0]["old_price"] == 5000.0
    assert drops[0]["new_price"] == 4500.0


def test_favorites_check_drops_no_change():
    """No drops detected when price is stable."""
    storage = RozetkaStorage(":memory:")
    tracker = RozetkaPriceTracker(storage)
    fav = RozetkaFavorites(storage, price_tracker=tracker)

    card = _card("iPad", 15000.0, ad_id="r-ipad")
    storage.save_ads([card])
    storage.save_ads([card])
    fav.add(card.fingerprint)

    drops = fav.check_drops()
    assert len(drops) == 0
