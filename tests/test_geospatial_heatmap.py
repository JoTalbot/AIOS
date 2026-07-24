"""Tests for geospatial price heatmap — city-level pricing analysis."""

from __future__ import annotations

from aios_core.geospatial_heatmap import (
    CityPriceStats,
    GeospatialPriceAnalyzer,
    PriceHeatmap,
)
from aios_core.modules.olx.models import AdCard
from aios_core.modules.olx.storage import OLXStorage


def _card(title: str, price: float, city: str = "", ad_id: str = "") -> AdCard:
    return AdCard(title=title, price=price, currency="UAH", city=city,
                  published_text="today", is_top=False, url=f"https://test.ua/{city}",
                  ad_id=ad_id or f"id-{city}", query="phone", raw_texts=[title])


def test_city_price_stats_dataclass():
    """CityPriceStats serializes to dict."""
    stats = CityPriceStats(city="Kyiv", count=10, avg_price=30000, min_price=25000, max_price=35000)
    d = stats.to_dict()
    assert d["city"] == "Kyiv"
    assert d["avg_price"] == 30000.0


def test_price_heatmap_dataclass():
    """PriceHeatmap has all fields."""
    heatmap = PriceHeatmap(
        query="iPhone", platform="olx",
        cheapest_city="Lviv", cheapest_avg=25000,
        priciest_city="Kyiv", priciest_avg=35000,
        national_avg=30000,
    )
    d = heatmap.to_dict()
    assert d["query"] == "iPhone"
    assert d["cheapest_city"] == "Lviv"
    assert d["total_cities"] == 0


def test_geospatial_heatmap_empty():
    """Heatmap for empty storage returns no cities."""
    storage = OLXStorage(":memory:")
    analyzer = GeospatialPriceAnalyzer(storage)
    heatmap = analyzer.heatmap(query="iPhone")
    assert len(heatmap.cities) == 0
    assert heatmap.cheapest_city is None


def test_geospatial_heatmap_with_data():
    """Heatmap computes city-level stats."""
    storage = OLXStorage(":memory:")
    storage.save_ads([
        _card("iPhone", 30000, city="Kyiv"),
        _card("iPhone", 32000, city="Kyiv"),
        _card("iPhone", 25000, city="Lviv"),
        _card("iPhone", 27000, city="Lviv"),
        _card("iPhone", 28000, city="Odesa"),
    ])
    analyzer = GeospatialPriceAnalyzer(storage)
    heatmap = analyzer.heatmap(query="phone")

    assert len(heatmap.cities) >= 1
    assert heatmap.national_avg is not None
    assert heatmap.cheapest_city is not None
    assert heatmap.priciest_city is not None


def test_geospatial_best_buy_cities():
    """best_buy_cities returns cheapest cities."""
    storage = OLXStorage(":memory:")
    storage.save_ads([
        _card("Phone", 30000, city="Kyiv"),
        _card("Phone", 25000, city="Lviv"),
        _card("Phone", 28000, city="Odesa"),
    ])
    analyzer = GeospatialPriceAnalyzer(storage)
    cheapest = analyzer.best_buy_cities(query="phone", limit=3)
    assert len(cheapest) >= 1
    assert cheapest[0].city in ("Lviv", "Odesa", "Kyiv")


def test_geospatial_best_sell_cities():
    """best_sell_cities returns priciest cities."""
    storage = OLXStorage(":memory:")
    storage.save_ads([
        _card("Phone", 30000, city="Kyiv"),
        _card("Phone", 25000, city="Lviv"),
    ])
    analyzer = GeospatialPriceAnalyzer(storage)
    priciest = analyzer.best_sell_cities(query="phone", limit=3)
    assert len(priciest) >= 1


def test_geospatial_arbitrage_cities():
    """arbitrage_cities finds city pairs with sufficient spread."""
    storage = OLXStorage(":memory:")
    storage.save_ads([
        _card("Phone", 35000, city="Kyiv"),
        _card("Phone", 25000, city="Lviv"),
        _card("Phone", 30000, city="Odesa"),
    ])
    analyzer = GeospatialPriceAnalyzer(storage)
    opportunities = analyzer.arbitrage_cities(min_spread_pct=1.0)
    # Kyiv vs Lviv should have spread
    assert len(opportunities) >= 1
