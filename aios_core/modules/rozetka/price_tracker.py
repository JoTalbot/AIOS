"""Rozetka.ua price tracker — monitors price changes and sends drop alerts.

Tracks product prices over time, detects drops, and notifies via webhook.
Uses RozetkaStorage for persistence and RozetkaCollector for data gathering.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional

from aios_core.modules.rozetka.storage import RozetkaStorage


class PriceDropAlert:
    """Represents a price drop event for a tracked product."""

    def __init__(
        self,
        fingerprint: str,
        title: str,
        old_price: float,
        new_price: float,
        url: str,
        drop_pct: float,
        seen_at: str,
    ) -> None:
        """Initialize PriceDropAlert."""
        self.fingerprint = fingerprint
        self.title = title
        self.old_price = old_price
        self.new_price = new_price
        self.url = url
        self.drop_pct = drop_pct
        self.seen_at = seen_at

    def to_dict(self) -> dict[str, object]:
        """Convert alert to a plain dict for JSON serialization."""
        return {
            "fingerprint": self.fingerprint,
            "title": self.title,
            "old_price": self.old_price,
            "new_price": self.new_price,
            "url": self.url,
            "drop_pct": round(self.drop_pct, 2),
            "seen_at": self.seen_at,
        }


class RozetkaPriceTracker:
    """Price tracker for Rozetka.ua products.

    Scans stored sightings for price drops and emits alerts.
    Threshold configurable via ``min_drop_pct`` (default 5%).
    """

    def __init__(
        self,
        storage: RozetkaStorage,
        min_drop_pct: float = 5.0,
        min_absolute_drop: float = 1.0,
    ) -> None:
        """Initialize RozetkaPriceTracker.

        Args:
            storage: RozetkaStorage instance for querying price history.
            min_drop_pct: Minimum percentage drop to trigger an alert (default 5%).
            min_absolute_drop: Minimum absolute price drop to trigger an alert (default 1.0 UAH).
        """
        self.storage = storage
        self.min_drop_pct = min_drop_pct
        self.min_absolute_drop = min_absolute_drop

    def detect_drops(self, since: str | None = None) -> list[PriceDropAlert]:
        """Scan sightings for price drops since the given timestamp.

        Args:
            since: ISO timestamp to filter sightings. If None, checks all history.

        Returns:
            List of PriceDropAlert objects for qualifying drops.
        """
        alerts: list[PriceDropAlert] = []
        ads = self.storage.get_ads()

        for ad in ads:
            fp = ad.fingerprint
            history = self.storage.price_history(fp)
            if len(history) < 2:
                continue

            # Find the most recent sighting and the highest prior price
            latest = history[-1]
            prior_prices = [h["price"] for h in history[:-1] if h.get("price") is not None]

            if not prior_prices or latest.get("price") is None:
                continue

            old_price = max(prior_prices)
            new_price = latest["price"]

            if old_price <= 0:
                continue

            if since and latest.get("seen_at", "") < since:
                continue

            drop_pct = ((old_price - new_price) / old_price) * 100
            abs_drop = old_price - new_price

            if drop_pct >= self.min_drop_pct and abs_drop >= self.min_absolute_drop:
                alerts.append(
                    PriceDropAlert(
                        fingerprint=fp,
                        title=ad.title,
                        old_price=old_price,
                        new_price=new_price,
                        url=ad.url,
                        drop_pct=drop_pct,
                        seen_at=latest.get("seen_at", datetime.now(timezone.utc).isoformat()),
                    )
                )

        return alerts

    def track_product(self, fingerprint: str) -> dict[str, object]:
        """Get price tracking stats for a specific product.

        Args:
            fingerprint: Product fingerprint to track.

        Returns:
            Dict with current_price, min_price, max_price, price_count, last_change.
        """
        history = self.storage.price_history(fingerprint)
        if not history:
            return {"fingerprint": fingerprint, "price_count": 0}

        prices = [h["price"] for h in history if h.get("price") is not None]
        current = prices[-1] if prices else None

        return {
            "fingerprint": fingerprint,
            "current_price": current,
            "min_price": min(prices) if prices else None,
            "max_price": max(prices) if prices else None,
            "price_count": len(prices),
            "last_change": history[-1].get("seen_at"),
            "history": history,
        }
