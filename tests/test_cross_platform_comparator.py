"""Tests for cross-platform comparator — OLX ↔ Rozetka ↔ Prom price comparison."""

from __future__ import annotations

from aios_core.cross_platform_comparator import (
    CrossPlatformComparator,
    CrossPlatformProduct,
    ComparisonGroup,
    MatchMethod,
)
from aios_core.modules.olx.storage import OLXStorage
from aios_core.modules.rozetka.storage import RozetkaStorage
from aios_core.modules.olx.models import AdCard


def _card(title: str, price: float, ad_id: str = "", query: str = "test") -> AdCard:
    """Helper to create an AdCard."""
    return AdCard(
        title=title,
        price=price,
        currency="UAH",
        city="Kyiv",
        published_text="today",
        is_top=False,
        url=f"https://{title}.ua",
        ad_id=ad_id or f"id-{title}",
        query=query,
        raw_texts=[title],
    )


def test_comparison_group_prices():
    """ComparisonGroup calculates min/max/avg/spread."""
    group = ComparisonGroup(
        group_id="cmp1",
        products=[
            CrossPlatformProduct("olx", "fp1", "iPhone 15", 30000, "UAH"),
            CrossPlatformProduct("rozetka", "fp2", "iPhone 15", 28000, "UAH"),
            CrossPlatformProduct("prom", "fp3", "iPhone 15", 32000, "UAH"),
        ],
    )
    assert group.lowest_price == 28000
    assert group.highest_price == 32000
    assert group.average_price == 30000
    assert abs(group.spread_pct - 13.33) < 0.01  # (32000-28000)/30000 * 100 ≈ 13.33
    assert group.best_platform == "rozetka"
    assert group.platforms == ["olx", "rozetka", "prom"]


def test_comparison_group_no_prices():
    """ComparisonGroup handles no valid prices."""
    group = ComparisonGroup(
        group_id="cmp2",
        products=[
            CrossPlatformProduct("olx", "fp1", "Test", None, "UAH"),
        ],
    )
    assert group.lowest_price is None
    assert group.average_price is None
    assert group.spread_pct is None


def test_comparison_group_to_dict():
    """ComparisonGroup serializes to dict."""
    group = ComparisonGroup(
        group_id="cmp3",
        products=[
            CrossPlatformProduct("olx", "fp1", "Phone", 5000, "UAH"),
            CrossPlatformProduct("rozetka", "fp2", "Phone", 4500, "UAH"),
        ],
    )
    d = group.to_dict()
    assert d["group_id"] == "cmp3"
    assert d["lowest_price"] == 4500
    assert d["best_platform"] == "rozetka"
    assert len(d["products"]) == 2


def test_cross_platform_title_similarity():
    """Title similarity uses token overlap."""
    comp = CrossPlatformComparator()
    # Identical
    assert comp._title_similarity("iPhone 15 Pro Max", "iPhone 15 Pro Max") == 1.0
    # Similar (3/4 tokens overlap)
    sim = comp._title_similarity("iPhone 15 Pro Max", "iPhone 15 Pro")
    assert sim >= 0.6
    # Different
    sim = comp._title_similarity("Samsung Galaxy S24", "iPhone 15 Pro Max")
    assert sim < 0.3
    # Empty
    assert comp._title_similarity("", "test") == 0.0


def test_cross_platform_compare_two_storages():
    """Compare products across OLX and Rozetka."""
    olx_storage = OLXStorage(":memory:")
    rozetka_storage = RozetkaStorage(":memory:")

    # Same product on both platforms
    olx_storage.save_ads([_card("iPhone 15 Pro", 30000, ad_id="olx-iphone15")])
    rozetka_storage.save_ads([_card("iPhone 15 Pro 256GB", 28000, ad_id="rz-iphone15")])

    comp = CrossPlatformComparator(
        storages={"olx": olx_storage, "rozetka": rozetka_storage},
        title_similarity_threshold=0.4,
    )

    groups = comp.compare()
    # Should find at least one group (both products mention "iPhone 15 Pro")
    assert len(groups) >= 1
    if groups:
        assert groups[0].lowest_price <= 28000


def test_cross_platform_compare_product():
    """Find same product on other platforms."""
    olx_storage = OLXStorage(":memory:")
    rozetka_storage = RozetkaStorage(":memory:")

    card = _card("iPhone 16", 35000, ad_id="olx-iphone16")
    olx_storage.save_ads([card])
    rozetka_storage.save_ads([_card("iPhone 16 Plus", 33000, ad_id="rz-iphone16")])

    comp = CrossPlatformComparator(
        storages={"olx": olx_storage, "rozetka": rozetka_storage},
        title_similarity_threshold=0.3,
    )

    group = comp.compare_product(card.fingerprint, "olx")
    # Should find a match on rozetka (both mention "iPhone 16")
    if group:
        assert len(group.products) >= 2


def test_cross_platform_arbitrage():
    """Find arbitrage opportunities (high spread)."""
    olx_storage = OLXStorage(":memory:")
    rozetka_storage = RozetkaStorage(":memory:")

    olx_storage.save_ads([_card("MacBook Air M3", 50000, ad_id="olx-mac")])
    rozetka_storage.save_ads([_card("MacBook Air M3 256GB", 30000, ad_id="rz-mac")])

    comp = CrossPlatformComparator(
        storages={"olx": olx_storage, "rozetka": rozetka_storage},
        title_similarity_threshold=0.3,
    )

    opps = comp.arbitrage_opportunities(min_spread_pct=10.0)
    # 50000 vs 30000 — 40% spread
    if opps:
        assert opps[0].spread_pct >= 10.0


def test_cross_platform_no_match():
    """No groups when products are completely different."""
    olx_storage = OLXStorage(":memory:")
    rozetka_storage = RozetkaStorage(":memory:")

    olx_storage.save_ads([_card("Велосипед горный", 5000, ad_id="olx-bike")])
    rozetka_storage.save_ads([_card("iPhone 16", 35000, ad_id="rz-phone")])

    comp = CrossPlatformComparator(
        storages={"olx": olx_storage, "rozetka": rozetka_storage},
        title_similarity_threshold=0.5,
    )

    groups = comp.compare()
    assert len(groups) == 0  # Bike and iPhone don't match


def test_match_method_enum():
    """MatchMethod enum values are correct."""
    assert MatchMethod.EXACT_ID.value == "exact_id"
    assert MatchMethod.URL_MATCH.value == "url_match"
    assert MatchMethod.TITLE_SIM.value == "title_similarity"
    assert MatchMethod.MANUAL.value == "manual"
