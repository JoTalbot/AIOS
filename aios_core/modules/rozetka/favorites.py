"""Rozetka.ua favorites — add/remove/list favorite products with price alerts.

Reuses OLX favorites table schema via RozetkaStorage with Rozetka-specific
extensions: price drop notifications for tracked favorites.
"""

from __future__ import annotations

from aios_core.modules.rozetka.price_tracker import RozetkaPriceTracker
from aios_core.modules.rozetka.storage import RozetkaStorage


class RozetkaFavorites:
    """Manage favorite products on Rozetka.ua with price tracking.

    Wraps RozetkaStorage favorites methods and adds price-change awareness.
    """

    def __init__(
        self,
        storage: RozetkaStorage,
        price_tracker: RozetkaPriceTracker | None = None,
        min_drop_pct: float = 5.0,
    ) -> None:
        """Initialize RozetkaFavorites.

        Args:
            storage: RozetkaStorage instance.
            price_tracker: Optional price tracker for alerts.
            min_drop_pct: Minimum price drop percentage for favorite alerts.
        """
        self.storage = storage
        self.price_tracker = price_tracker or RozetkaPriceTracker(
            storage, min_drop_pct=min_drop_pct
        )
        self.min_drop_pct = min_drop_pct

    def add(self, fingerprint: str) -> bool:
        """Add a product to favorites.

        Args:
            fingerprint: Product fingerprint to add.

        Returns:
            True if newly added, False if already a favorite.
        """
        return self.storage.favorite_add(fingerprint)

    def remove(self, fingerprint: str) -> bool:
        """Remove a product from favorites.

        Args:
            fingerprint: Product fingerprint to remove.

        Returns:
            True if removed, False if not found.
        """
        return self.storage.favorite_remove(fingerprint)

    def list_all(self) -> list[str]:
        """Return all favorite product fingerprints."""
        return self.storage.favorites_list()

    def list_with_details(self) -> list[dict[str, object]]:
        """Return favorites with product details and current price."""
        fps = self.list_all()
        results: list[dict[str, object]] = []
        for fp in fps:
            ads = self.storage.get_ads()
            ad = None
            for a in ads:
                if a.fingerprint == fp:
                    ad = a
                    break
            if ad:
                stats = self.price_tracker.track_product(fp)
                results.append(
                    {
                        "fingerprint": fp,
                        "title": ad.title,
                        "price": ad.price,
                        "url": ad.url,
                        "min_price": stats.get("min_price"),
                        "max_price": stats.get("max_price"),
                        "price_count": stats.get("price_count", 0),
                    }
                )
        return results

    def check_drops(self) -> list[dict[str, object]]:
        """Check all favorites for price drops.

        Returns:
            List of dicts with fingerprint, old_price, new_price, drop_pct.
        """
        alerts: list[dict[str, object]] = []
        for fp in self.list_all():
            stats = self.price_tracker.track_product(fp)
            history = stats.get("history", [])
            if len(history) >= 2:
                prev_price = history[-2].get("price")
                curr_price = history[-1].get("price")
                if prev_price and curr_price and curr_price < prev_price:
                    drop_pct = ((prev_price - curr_price) / prev_price) * 100
                    if drop_pct >= self.min_drop_pct:
                        alerts.append(
                            {
                                "fingerprint": fp,
                                "old_price": prev_price,
                                "new_price": curr_price,
                                "drop_pct": round(drop_pct, 2),
                            }
                        )
        return alerts
