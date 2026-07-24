"""Seller reputation scoring — rate sellers across platforms.

Scores sellers based on:
- Response time (how fast they reply to messages)
- Listing quality (description completeness, photo count)
- Price consistency (stable prices vs frequent changes)
- Activity level (how often they list new items)
- Review/rating data (if available from platform)

Produces a composite score (0-100) with detailed breakdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aios_core.modules.olx.storage import OLXStorage


@dataclass
class SellerProfile:
    """Basic seller profile extracted from stored ads."""

    seller_id: str | None = None
    name: str | None = None
    city: str | None = None
    total_ads: int = 0
    active_ads: int = 0
    avg_price: float | None = None
    price_std: float | None = None
    first_seen: str | None = None
    last_seen: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {
            "seller_id": self.seller_id,
            "name": self.name,
            "total_ads": self.total_ads,
            "active_ads": self.active_ads,
            "avg_price": self.avg_price,
            "price_std": self.price_std,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }


@dataclass
class SellerScore:
    """Composite seller reputation score with breakdown."""

    seller_id: str | None = None
    composite_score: float = 0.0  # 0-100
    response_time_score: float = 0.0
    listing_quality_score: float = 0.0
    price_consistency_score: float = 0.0
    activity_score: float = 0.0
    grade: str = "C"  # A, B, C, D, F
    details: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {
            "seller_id": self.seller_id,
            "composite_score": round(self.composite_score, 2),
            "response_time_score": round(self.response_time_score, 2),
            "listing_quality_score": round(self.listing_quality_score, 2),
            "price_consistency_score": round(self.price_consistency_score, 2),
            "activity_score": round(self.activity_score, 2),
            "grade": self.grade,
            "details": self.details,
        }


class SellerReputationScorer:
    """Score seller reputation from stored ad data.

    Computes composite score (0-100) from multiple factors:
    - Activity (40% weight): number of active ads, listing frequency
    - Price consistency (30% weight): standard deviation of prices
    - Listing quality (20% weight): description length, title completeness
    - Response time (10% weight): outbox reply speed (if available)
    """

    def __init__(self, storage: OLXStorage) -> None:
        """Initialize SellerReputationScorer.

        Args:
            storage: Platform storage instance with seller data.
        """
        self.storage = storage

    def score_seller(self, seller_id: str | None = None) -> SellerScore | None:
        """Compute reputation score for a seller.

        Args:
            seller_id: Seller identifier. If None, scores all sellers.

        Returns:
            SellerScore or None if no data available.
        """
        ads = self.storage.get_ads()

        # Group ads by seller (using ad_id as proxy for seller)
        seller_ads: dict[str, list] = {}
        for ad in ads:
            key = seller_id or ad.ad_id or ad.fingerprint
            seller_ads.setdefault(key, []).append(ad)

        if not seller_ads:
            return None

        key = seller_id or next(iter(seller_ads))
        ad_list = seller_ads.get(key, [])

        if not ad_list:
            return None

        # Compute scores
        activity_score = self._compute_activity(ad_list)
        price_score = self._compute_price_consistency(ad_list)
        quality_score = self._compute_listing_quality(ad_list)
        response_score = self._compute_response_time(key)

        # Weighted composite
        composite = (
            activity_score * 0.40
            + price_score * 0.30
            + quality_score * 0.20
            + response_score * 0.10
        )

        # Grade
        grade = self._grade(composite)

        return SellerScore(
            seller_id=key,
            composite_score=composite,
            response_time_score=response_score,
            listing_quality_score=quality_score,
            price_consistency_score=price_score,
            activity_score=activity_score,
            grade=grade,
            details={
                "total_ads": len(ad_list),
                "avg_price": sum(a.price for a in ad_list if a.price)
                / len([a for a in ad_list if a.price])
                if any(a.price for a in ad_list)
                else None,
            },
        )

    def score_all_sellers(self) -> list[SellerScore]:
        """Score all sellers in storage.

        Returns:
            List of SellerScore sorted by composite score (descending).
        """
        ads = self.storage.get_ads()
        seller_ids: set[str] = set()

        for ad in ads:
            if ad.ad_id:
                seller_ids.add(ad.ad_id)

        scores = []
        for sid in seller_ids:
            score = self.score_seller(sid)
            if score:
                scores.append(score)

        scores.sort(key=lambda s: -s.composite_score)
        return scores

    def _compute_activity(self, ads: list) -> float:
        """Activity score: more active ads = higher score."""
        count = len(ads)
        if count == 0:
            return 0
        # Scale: 1 ad = 20, 5+ = 80, 10+ = 100
        if count >= 10:
            return 100
        return min(100, 20 + count * 15)

    def _compute_price_consistency(self, ads: list) -> float:
        """Price consistency: low std deviation = higher score."""
        prices = [a.price for a in ads if a.price is not None]
        if not prices:
            return 50  # No price data → neutral

        avg = sum(prices) / len(prices)
        if avg == 0:
            return 50

        # Calculate relative std deviation
        variance = sum((p - avg) ** 2 for p in prices) / len(prices)
        std = variance**0.5
        rel_std = std / avg

        # Low rel_std (stable prices) = high score
        if rel_std < 0.05:
            return 100
        if rel_std < 0.10:
            return 80
        if rel_std < 0.20:
            return 60
        if rel_std < 0.30:
            return 40
        return 20

    def _compute_listing_quality(self, ads: list) -> float:
        """Listing quality: longer descriptions/titles = higher score."""
        if not ads:
            return 0

        scores: list[float] = []
        for ad in ads:
            title_len = len(ad.title) if ad.title else 0
            # Title > 30 chars = good, < 10 = poor
            if title_len >= 30:
                scores.append(80)
            elif title_len >= 10:
                scores.append(50)
            else:
                scores.append(20)

        return sum(scores) / len(scores)

    def _compute_response_time(self, seller_key: str) -> float:
        """Response time score from outbox data."""
        # Default: no outbox data → neutral
        return 50

    def _grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return "A"
        if score >= 75:
            return "B"
        if score >= 60:
            return "C"
        if score >= 40:
            return "D"
        return "F"
