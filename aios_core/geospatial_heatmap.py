"""Geospatial price heatmap — city-level pricing analysis across platforms.

Analyzes price distribution across cities/regions for a given
product category, producing:
- City-level average prices
- Price heatmap data (for visualization)
- Regional price comparison
- Best/worst cities for buying/selling

Uses storage data (OLXStorage and subclasses) for geospatial analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from aios_core.modules.olx.storage import OLXStorage


@dataclass
class CityPriceStats:
    """Price statistics for a specific city."""

    city: str
    count: int = 0
    avg_price: float = 0.0
    min_price: float | None = None
    max_price: float | None = None
    std_price: float | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {
            "city": self.city,
            "count": self.count,
            "avg_price": round(self.avg_price, 2),
            "min_price": self.min_price,
            "max_price": self.max_price,
            "std_price": round(self.std_price, 2) if self.std_price else None,
        }


@dataclass
class PriceHeatmap:
    """Full price heatmap across cities for a product category."""

    query: str | None = None
    platform: str = ""
    cities: list[CityPriceStats] = field(default_factory=list)
    cheapest_city: str | None = None
    cheapest_avg: float | None = None
    priciest_city: str | None = None
    priciest_avg: float | None = None
    national_avg: float | None = None
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {
            "query": self.query,
            "platform": self.platform,
            "cities": [c.to_dict() for c in self.cities],
            "cheapest_city": self.cheapest_city,
            "cheapest_avg": self.cheapest_avg,
            "priciest_city": self.priciest_city,
            "priciest_avg": self.priciest_avg,
            "national_avg": round(self.national_avg, 2) if self.national_avg else None,
            "generated_at": self.generated_at,
            "total_cities": len(self.cities),
        }


class GeospatialPriceAnalyzer:
    """Analyze price distribution across cities for geospatial heatmap.

    Uses platform storage to compute city-level price statistics
    and produce heatmap visualization data.
    """

    def __init__(self, storage: OLXStorage, platform: str = "olx") -> None:
        """Initialize GeospatialPriceAnalyzer.

        Args:
            storage: Platform storage instance.
            platform: Platform name for context.
        """
        self.storage = storage
        self.platform = platform

    def heatmap(self, query: str | None = None) -> PriceHeatmap:
        """Generate price heatmap for a product category.

        Args:
            query: Optional search query to filter products.

        Returns:
            PriceHeatmap with city-level statistics.
        """
        ads = self.storage.get_ads(query=query)

        # Group by city
        city_prices: dict[str, list[float]] = {}
        for ad in ads:
            if ad.city and ad.price is not None:
                city_prices.setdefault(ad.city, []).append(ad.price)

        # Compute stats per city
        cities: list[CityPriceStats] = []
        for city, prices in city_prices.items():
            avg = sum(prices) / len(prices)
            variance = sum((p - avg) ** 2 for p in prices) / len(prices)
            std = variance**0.5

            cities.append(
                CityPriceStats(
                    city=city,
                    count=len(prices),
                    avg_price=avg,
                    min_price=min(prices),
                    max_price=max(prices),
                    std_price=std,
                )
            )

        # Sort by avg_price (ascending)
        cities.sort(key=lambda c: c.avg_price)

        # Find cheapest/priciest
        cheapest_city = cities[0].city if cities else None
        cheapest_avg = cities[0].avg_price if cities else None
        priciest_city = cities[-1].city if cities else None
        priciest_avg = cities[-1].avg_price if cities else None

        # National average
        all_prices = [p for ps in city_prices.values() for p in ps]
        national_avg = sum(all_prices) / len(all_prices) if all_prices else None

        return PriceHeatmap(
            query=query,
            platform=self.platform,
            cities=cities,
            cheapest_city=cheapest_city,
            cheapest_avg=round(cheapest_avg, 2) if cheapest_avg else None,
            priciest_city=priciest_city,
            priciest_avg=round(priciest_avg, 2) if priciest_avg else None,
            national_avg=round(national_avg, 2) if national_avg else None,
        )

    def best_buy_cities(
        self, query: str | None = None, limit: int = 5
    ) -> list[CityPriceStats]:
        """Find cheapest cities for buying a product.

        Args:
            query: Search query.
            limit: Number of cities to return.

        Returns:
            List of CityPriceStats sorted by avg_price (ascending).
        """
        heatmap = self.heatmap(query=query)
        return heatmap.cities[:limit]

    def best_sell_cities(
        self, query: str | None = None, limit: int = 5
    ) -> list[CityPriceStats]:
        """Find priciest cities for selling a product.

        Args:
            query: Search query.
            limit: Number of cities to return.

        Returns:
            List of CityPriceStats sorted by avg_price (descending).
        """
        heatmap = self.heatmap(query=query)
        return sorted(heatmap.cities, key=lambda c: -c.avg_price)[:limit]

    def arbitrage_cities(
        self, query: str | None = None, min_spread_pct: float = 10.0
    ) -> list[dict[str, object]]:
        """Find city pairs with price arbitrage opportunities.

        Args:
            query: Search query.
            min_spread_pct: Minimum price spread percentage.

        Returns:
            List of buy_city/sell_city/spread_pct dicts.
        """
        heatmap = self.heatmap(query=query)
        if not heatmap.national_avg or heatmap.national_avg == 0:
            return []

        opportunities: list[dict[str, object]] = []
        for cheap in heatmap.cities:
            for pricey in heatmap.cities:
                if cheap.city == pricey.city:
                    continue
                spread_pct = (
                    (pricey.avg_price - cheap.avg_price) / heatmap.national_avg
                ) * 100
                if spread_pct >= min_spread_pct:
                    opportunities.append(
                        {
                            "buy_city": cheap.city,
                            "buy_avg": round(cheap.avg_price, 2),
                            "sell_city": pricey.city,
                            "sell_avg": round(pricey.avg_price, 2),
                            "spread_pct": round(spread_pct, 2),
                        }
                    )

        opportunities.sort(key=lambda o: -o["spread_pct"])
        return opportunities
