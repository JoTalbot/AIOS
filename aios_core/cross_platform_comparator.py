"""Cross-platform comparator — compares prices across OLX, Rozetka, Prom, Shafa.

Finds the same (or similar) product on multiple marketplaces and compares:
- Price (lowest, average, spread)
- Availability (in stock, out of stock)
- Seller rating / reviews
- Delivery options

Provides actionable recommendations:
- Buy on platform X (lowest price)
- Sell on platform Y (highest average)
- Price arbitrage opportunities
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from aios_core.modules.olx.storage import OLXStorage
from aios_core.modules.rozetka.storage import RozetkaStorage


class MatchMethod(Enum):
    """How products were matched across platforms."""

    EXACT_ID = "exact_id"          # Same ad_id / product_id
    URL_MATCH = "url_match"        # Same product URL
    TITLE_SIM = "title_similarity" # Similar title (fuzzy)
    MANUAL = "manual"              # Manually linked


@dataclass
class CrossPlatformProduct:
    """A product found on one platform within a comparison group."""

    platform: str
    fingerprint: str
    title: str
    price: float | None
    currency: str
    url: str | None = None
    city: str | None = None
    is_active: bool = True
    match_method: MatchMethod = MatchMethod.TITLE_SIM


@dataclass
class ComparisonGroup:
    """Group of the same/similar product across multiple platforms."""

    group_id: str
    products: list[CrossPlatformProduct] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def prices(self) -> list[float]:
        """All valid prices in the group."""
        return [p.price for p in self.products if p.price is not None]

    @property
    def lowest_price(self) -> float | None:
        """Minimum price across platforms."""
        return min(self.prices) if self.prices else None

    @property
    def highest_price(self) -> float | None:
        """Maximum price across platforms."""
        return max(self.prices) if self.prices else None

    @property
    def average_price(self) -> float | None:
        """Average price across platforms."""
        return sum(self.prices) / len(self.prices) if self.prices else None

    @property
    def spread_pct(self) -> float | None:
        """Price spread percentage (highest - lowest) / average."""
        avg = self.average_price
        if avg and avg > 0:
            return ((self.highest_price - self.lowest_price) / avg) * 100
        return None

    @property
    def best_platform(self) -> str | None:
        """Platform with the lowest price."""
        if not self.prices:
            return None
        min_price = self.lowest_price
        for p in self.products:
            if p.price == min_price:
                return p.platform
        return None

    @property
    def platforms(self) -> list[str]:
        """All platforms in this group."""
        return [p.platform for p in self.products]

    def to_dict(self) -> dict[str, object]:
        """Serialize comparison group to dict."""
        return {
            "group_id": self.group_id,
            "platforms": self.platforms,
            "products": [p.__dict__ for p in self.products],
            "lowest_price": self.lowest_price,
            "highest_price": self.highest_price,
            "average_price": round(self.average_price, 2) if self.average_price else None,
            "spread_pct": round(self.spread_pct, 2) if self.spread_pct else None,
            "best_platform": self.best_platform,
            "created_at": self.created_at,
        }


class CrossPlatformComparator:
    """Compare products across OLX, Rozetka, Prom, Shafa.

    Matches products by title similarity (fuzzy) and exact IDs,
    then generates comparison groups with price analysis.
    """

    def __init__(
        self,
        storages: dict[str, OLXStorage | RozetkaStorage] | None = None,
        title_similarity_threshold: float = 0.6,
    ) -> None:
        """Initialize CrossPlatformComparator.

        Args:
            storages: Dict of platform_name → Storage instances.
            title_similarity_threshold: Minimum similarity score to group products (0.0-1.0).
        """
        self.storages = storages or {}
        self.title_similarity_threshold = title_similarity_threshold

    def _title_similarity(self, a: str, b: str) -> float:
        """Compute normalized title similarity using token overlap.

        Simple but fast — no external dependencies.
        """
        if not a or not b:
            return 0.0
        tokens_a = set(a.lower().split())
        tokens_b = set(b.lower().split())
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union)

    def compare(self, query: str | None = None) -> list[ComparisonGroup]:
        """Find and compare products across all registered platforms.

        Args:
            query: Optional search query to filter products.

        Returns:
            List of ComparisonGroup with matched products.
        """
        all_products: list[CrossPlatformProduct] = []

        for platform_name, storage in self.storages.items():
            ads = storage.get_ads(query=query)
            for ad in ads:
                all_products.append(
                    CrossPlatformProduct(
                        platform=platform_name,
                        fingerprint=ad.fingerprint,
                        title=ad.title,
                        price=ad.price,
                        currency=ad.currency or "UAH",
                        url=ad.url,
                        city=ad.city,
                        is_active=True,
                        match_method=MatchMethod.TITLE_SIM,
                    )
                )

        return self._group_products(all_products)

    def compare_product(self, fingerprint: str, platform: str) -> ComparisonGroup | None:
        """Find the same product on other platforms.

        Args:
            fingerprint: Source product fingerprint.
            platform: Source platform name.

        Returns:
            ComparisonGroup with matches, or None if no matches found.
        """
        # Find source product
        storage = self.storages.get(platform)
        if not storage:
            return None

        ads = storage.get_ads()
        source_ad = None
        for ad in ads:
            if ad.fingerprint == fingerprint:
                source_ad = ad
                break

        if not source_ad:
            return None

        # Search on other platforms
        products = [
            CrossPlatformProduct(
                platform=platform,
                fingerprint=source_ad.fingerprint,
                title=source_ad.title,
                price=source_ad.price,
                currency=source_ad.currency or "UAH",
                url=source_ad.url,
                city=source_ad.city,
                match_method=MatchMethod.EXACT_ID,
            )
        ]

        for other_name, other_storage in self.storages.items():
            if other_name == platform:
                continue
            other_ads = other_storage.get_ads()
            for ad in other_ads:
                sim = self._title_similarity(source_ad.title, ad.title)
                if sim >= self.title_similarity_threshold:
                    products.append(
                        CrossPlatformProduct(
                            platform=other_name,
                            fingerprint=ad.fingerprint,
                            title=ad.title,
                            price=ad.price,
                            currency=ad.currency or "UAH",
                            url=ad.url,
                            city=ad.city,
                            match_method=MatchMethod.TITLE_SIM,
                        )
                    )

        if len(products) < 2:
            return None

        group_id = f"cmp_{hash(source_ad.title.lower()) % 100000}"
        return ComparisonGroup(group_id=group_id, products=products)

    def _group_products(self, products: list[CrossPlatformProduct]) -> list[ComparisonGroup]:
        """Group products by title similarity across platforms."""
        groups: list[ComparisonGroup] = []
        used: set[int] = set()

        for i, p1 in enumerate(products):
            if i in used:
                continue
            group_products = [p1]
            used.add(i)

            for j, p2 in enumerate(products):
                if j in used:
                    continue
                if p1.platform == p2.platform:
                    continue  # Skip same-platform products
                sim = self._title_similarity(p1.title, p2.title)
                if sim >= self.title_similarity_threshold:
                    group_products.append(p2)
                    used.add(j)

            if len(group_products) >= 2:
                group_id = f"cmp_{hash(p1.title.lower()) % 100000}"
                groups.append(ComparisonGroup(group_id=group_id, products=group_products))

        return groups

    def arbitrage_opportunities(self, min_spread_pct: float = 10.0) -> list[ComparisonGroup]:
        """Find arbitrage opportunities where spread ≥ min_spread_pct.

        Args:
            min_spread_pct: Minimum price spread percentage for arbitrage.

        Returns:
            ComparisonGroups with sufficient spread for arbitrage.
        """
        all_groups = self.compare()
        return [g for g in all_groups if g.spread_pct and g.spread_pct >= min_spread_pct]
