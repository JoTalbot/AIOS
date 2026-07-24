"""AIOS OLX Android Agent — search subscriptions & favorite-ad watch."""

from __future__ import annotations

from typing import Dict, List, Optional

from .analytics import PriceTracker
from .models import AdCard


class SubscriptionManager:
    """Named saved searches with price/city filters and new-ad alerts.

    A subscription matches an ad when the ad was collected for the same
    query (or its title contains all query tokens) *and* it passes the
    price/city filters. ``check_new`` is meant to run right after a
    collection cycle with the freshly stored cards.
    """

    def __init__(self, storage):
        """Initialize SubscriptionManager."""
        self.storage = storage

    def add(
        self,
        name: str,
        query: str,
        min_price: float | None = None,
        max_price: float | None = None,
        city: str | None = None,
    ) -> int:
        """Add a search subscription with filters."""
        return self.storage.subscription_add(name, query, min_price, max_price, city)

    def list(self) -> List[Dict[str, object]]:
        """List all watched fingerprints."""
        return self.storage.subscriptions_list()

        """Remove a fingerprint from the watch list."""
    def remove(self, subscription_id: int) -> bool:
        """Remove a fingerprint from the watch list."""
        return self.storage.subscription_remove(subscription_id)

    @staticmethod
    def matches(subscription: Dict[str, object], card: AdCard) -> bool:
        """Whether a collected card passes the subscription filters."""
        same_query = (card.query or "").strip().lower() == (
            subscription["query"] or ""
        ).strip().lower()
        if not same_query:
            tokens = [t for t in (subscription["query"] or "").lower().split() if t]
            title = (card.title or "").lower()
            if not (tokens and all(token in title for token in tokens)):
                return False
        if subscription.get("city"):
            if (card.city or "").strip().lower() != subscription["city"].strip().lower():
                return False
        if subscription.get("min_price") is not None:
            if card.price is None or card.price < subscription["min_price"]:
                return False
        if subscription.get("max_price") is not None:
            if card.price is None or card.price > subscription["max_price"]:
                return False
        return True

    def check_new(self, new_cards: List[AdCard]) -> List[Dict[str, object]]:
        """Match fresh cards against all subscriptions; returns alert payloads."""
        alerts: List[Dict[str, object]] = []
        for subscription in self.storage.subscriptions_list():
            hits = [card for card in new_cards if self.matches(subscription, card)]
            if not hits:
                continue
            self.storage.subscription_touch(subscription["id"])
            alerts.append(
                {
                    "type": "subscription_new_ads",
                    "subscription_id": subscription["id"],
                    "subscription": subscription["name"],
                    "query": subscription["query"],
                    "new_count": len(hits),
                    "ads": [card.to_dict() for card in hits],
                }
            )
        return alerts


class FavoritesWatch:
    """Tracks user-favorite ads and surfaces their price drops."""

    def __init__(self, storage):
        """Initialize FavoritesWatch."""
        self.storage = storage
        """Add a fingerprint to the watch list."""

    def add(self, fingerprint: str) -> bool:
        """Remove a fingerprint from the watch list."""
        return self.storage.favorite_add(fingerprint)

    def remove(self, fingerprint: str) -> bool:
        """Remove a fingerprint from the watch list."""
        return self.storage.favorite_remove(fingerprint)

    def list(self) -> List[Dict[str, object]]:
        """Favorite fingerprints joined with the ad payloads."""
        fps = set(self.storage.favorites_list())
        return [ad.to_dict() for ad in self.storage.get_ads() if ad.fingerprint in fps]

    def price_alerts(self) -> List[Dict[str, object]]:
        """Price drops restricted to favorite ads."""
        fps = set(self.storage.favorites_list())
        if not fps:
            return []
        tracker = PriceTracker(self.storage)
        alerts: List[Dict[str, object]] = []
        for drop in tracker.price_drops():
            if drop.fingerprint not in fps:
                continue
            payload = drop.to_dict()
            payload["type"] = "favorite_price_drop"
            alerts.append(payload)
        return alerts
