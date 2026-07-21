"""AIOS OLX Android Agent — competitor surveillance driven by own listings.

Derives a market query from each own listing, links similar market ads to it
(`olx_competitor_links`), and reports the competitive position of every own
ad: who's cheaper, who's new in the niche, and where you rank by price.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .analytics import _tokenize
from .models import AdCard
from .own_ads import OwnAd

_SIMILARITY_THRESHOLD = 0.30


def derive_query(title: str, max_tokens: int = 3) -> str:
    """Best search query for a listing title (top content tokens)."""
    tokens = _tokenize(title)
    return " ".join(tokens[:max_tokens])


def title_similarity(a: str, b: str) -> float:
    """Jaccard similarity over title token sets."""
    tokens_a = set(_tokenize(a))
    tokens_b = set(_tokenize(b))
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def link_score(own: OwnAd, candidate: AdCard) -> float:
    """Combined similarity: title Jaccard + price proximity + city bonus."""
    title_sim = title_similarity(own.title, candidate.title or "")
    score = title_sim
    if own.price and candidate.price:
        ratio = min(own.price, candidate.price) / max(own.price, candidate.price)
        score += 0.15 * ratio
        # Competing means roughly the same market segment, not identical price.
    if own.price and candidate.price:
        if ratio >= 0.5:
            score += 0.10
    if candidate.city:
        score += 0.05
    return min(score, 1.0)


class CompetitiveWatch:
    """Links market ads to own listings and grades competitive position."""

    def __init__(self, storage, threshold: float = _SIMILARITY_THRESHOLD):
        self.storage = storage
        self.threshold = threshold

    def refresh(
        self,
        own_ads: List[OwnAd],
        candidates: Optional[List[AdCard]] = None,
        seen_at: Optional[str] = None,
    ) -> Dict[str, object]:
        """(Re)link every own ad against its market candidates.

        Returns counts plus per-own-ad summaries with undercut information.
        """
        if candidates is None:
            candidates = self.storage.get_ads(active_only=True)
        now = seen_at or datetime.now(timezone.utc).isoformat()
        new_links = 0
        per_own: Dict[str, Dict[str, object]] = {}

        for own in own_ads:
            linked = 0
            cheaper = 0
            for candidate in candidates:
                score = link_score(own, candidate)
                if score < self.threshold:
                    continue
                is_new = self.storage.competitor_link_upsert(
                    own.fingerprint, candidate.fingerprint, score, seen_at=now
                )
                new_links += int(is_new)
                linked += 1
                if own.price and candidate.price and candidate.price < own.price:
                    cheaper += 1
            per_own[own.fingerprint] = {
                "title": own.title,
                "my_price": own.price,
                "linked_competitors": linked,
                "cheaper_competitors": cheaper,
                "query_hint": derive_query(own.title),
            }

        total = sum(len(self.storage.competitor_links(o.fingerprint)) for o in own_ads)
        return {"new_links": new_links, "total_links": total, "per_own": per_own}

    def report(self, own_fingerprint: str) -> Dict[str, object]:
        """Full competitive picture for one own listing."""
        links = self.storage.competitor_links(own_fingerprint)
        ads = {
            ad.fingerprint: ad for ad in self.storage.get_ads(limit=1000)
        }
        competitors: List[Dict[str, object]] = []
        for link in links:
            ad = ads.get(link["competitor_fingerprint"])
            entry = dict(link)
            if ad is not None:
                entry["ad"] = ad.to_dict()
            competitors.append(entry)

        prices = [
            entry["ad"]["price"]
            for entry in competitors
            if entry.get("ad") and entry["ad"].get("price") is not None
        ]
        prices.sort()
        return {
            "own_fingerprint": own_fingerprint,
            "competitors_count": len(competitors),
            "cheapest_price": prices[0] if prices else None,
            "most_expensive_price": prices[-1] if prices else None,
            "competitors": competitors,
        }

    def price_position(
        self, own: OwnAd, candidates: Optional[List[AdCard]] = None
    ) -> Dict[str, object]:
        """Where my price stands among similar ads (1 = cheapest)."""
        if candidates is None:
            candidates = self.storage.get_ads(active_only=True)
        similar = [
            card
            for card in candidates
            if card.price is not None
            and link_score(own, card) >= self.threshold
        ]
        prices = sorted(card.price for card in similar)
        if not prices or own.price is None:
            return {
                "rank": None,
                "of": len(prices),
                "cheaper_competitors": 0,
                "median_competitor_price": None,
            }
        cheaper = sum(1 for price in prices if price < own.price)
        mid = len(prices) // 2
        median = prices[mid] if len(prices) % 2 else (prices[mid - 1] + prices[mid]) / 2
        return {
            "rank": cheaper + 1,
            "of": len(prices) + 1,
            "cheaper_competitors": cheaper,
            "median_competitor_price": median,
        }
