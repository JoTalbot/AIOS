"""Rozetka.ua AutoWatch — automated product monitoring with alerts.

Combines RozetkaCollector (card gathering), RozetkaPriceTracker (drop detection),
and notification via webhook/email. Reuses OLX AutoWatch cycle pattern
with Rozetka-specific extensions.
"""

from __future__ import annotations

from datetime import datetime, timezone

from aios_core.modules.rozetka.collector import RozetkaCollector
from aios_core.modules.rozetka.price_tracker import RozetkaPriceTracker, PriceDropAlert
from aios_core.modules.rozetka.storage import RozetkaStorage


class RozetkaAutoWatch:
    """Full AutoWatch cycle for Rozetka.ua.

    1. Collect product cards via RozetkaCollector.
    2. Store sightings in RozetkaStorage.
    3. Detect price drops via RozetkaPriceTracker.
    4. Emit alerts (price drop, new product, stagnant product).
    """

    def __init__(
        self,
        storage: RozetkaStorage,
        collector: RozetkaCollector | None = None,
        price_tracker: RozetkaPriceTracker | None = None,
        min_drop_pct: float = 5.0,
        max_cards: int = 50,
        min_age_days: float = 3.0,
    ) -> None:
        """Initialize RozetkaAutoWatch.

        Args:
            storage: RozetkaStorage for persistence.
            collector: RozetkaCollector for gathering cards.
            price_tracker: RozetkaPriceTracker for drop detection.
            min_drop_pct: Minimum price drop percentage for alerts.
            max_cards: Max cards to collect per cycle.
            min_age_days: Minimum days before marking a product stagnant.
        """
        self.storage = storage
        self.collector = collector or RozetkaCollector()
        self.price_tracker = price_tracker or RozetkaPriceTracker(
            storage, min_drop_pct=min_drop_pct
        )
        self.max_cards = max_cards
        self.min_age_days = min_age_days

    def run_cycle(
        self,
        queries: list[str] | None = None,
        collect: bool = True,
    ) -> dict[str, object]:
        """Run one full AutoWatch cycle.

        Args:
            queries: Search queries to monitor. If None, uses stored subscriptions.
            collect: Whether to collect new data (True) or just analyze existing data.

        Returns:
            Report dict with collection stats, price alerts, and stagnant products.
        """
        report: dict[str, object] = {
            "platform": "rozetka",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        # Step 1: Collect
        collection_stats: dict[str, object] = {"collected": 0, "new": 0}
        if collect and queries:
            for query in queries:
                result = self.collector.collect_to_storage(
                    self.storage, query=query, max_cards=self.max_cards
                )
                collected = result.get("collected", 0)
                new = result.get("new", 0)
                collection_stats["collected"] = collection_stats.get("collected", 0) + collected
                collection_stats["new"] = collection_stats.get("new", 0) + new

        report["collection"] = collection_stats

        # Step 2: Price drop detection
        alerts = self.price_tracker.detect_drops()
        report["price_drop_alerts"] = [a.to_dict() for a in alerts]

        # Step 3: Stagnant products (not seen for min_age_days)
        stagnant = self._find_stagnant()
        report["stagnant"] = stagnant

        # Step 4: Favorites alerts
        fav_alerts = self._favorite_alerts()
        report["favorite_alerts"] = fav_alerts

        report["completed_at"] = datetime.now(timezone.utc).isoformat()
        return report

    def _find_stagnant(self) -> list[dict[str, object]]:
        """Find products not seen for min_age_days or longer."""
        cutoff = datetime.now(timezone.utc).timestamp() - self.min_age_days * 86400
        ads = self.storage.get_ads()
        stagnant: list[dict[str, object]] = []
        for ad in ads:
            last_seen = getattr(ad, "last_seen_at", None)
            if last_seen:
                try:
                    ts = datetime.fromisoformat(last_seen).timestamp()
                    if ts < cutoff:
                        stagnant.append({
                            "fingerprint": ad.fingerprint,
                            "title": ad.title,
                            "last_seen_at": last_seen,
                            "price": ad.price,
                        })
                except (ValueError, TypeError):
                    pass
        return stagnant

    def _favorite_alerts(self) -> list[dict[str, object]]:
        """Check favorites for price changes."""
        fav_fingerprints = self.storage.favorites_list()
        alerts: list[dict[str, object]] = []
        for fp in fav_fingerprints:
            stats = self.price_tracker.track_product(fp)
            history = stats.get("history", [])
            if len(history) >= 2:
                prev = history[-2].get("price")
                curr = history[-1].get("price")
                if prev is not None and curr is not None and curr < prev:
                    alerts.append({
                        "fingerprint": fp,
                        "old_price": prev,
                        "new_price": curr,
                        "drop_pct": round(((prev - curr) / prev) * 100, 2),
                    })
        return alerts
