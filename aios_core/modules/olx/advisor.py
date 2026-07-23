"""AIOS OLX Android Agent — strategy advisor.

Two kinds of output:

* :class:`ActionAdvice` — what to do with each own listing
  (KEEP / EDIT_PRICE / EDIT_CONTENT / REPOST / PROMOTE) with rationale;
* :class:`NewListingSuggestion` — what *new* listings are worth publishing:
  active market queries the portfolio doesn't cover yet, with target price
  and a seed title built from market keywords.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import median
from typing import Dict, List, Optional

from .analytics import RecommendationEngine
from .competitive import CompetitiveWatch, derive_query
from .own_ads import OwnAd, OwnAdsTracker
from .promotion import RepostPlanner

ACTION_KEEP = "KEEP"
ACTION_EDIT_PRICE = "EDIT_PRICE"
ACTION_EDIT_CONTENT = "EDIT_CONTENT"
ACTION_REPOST = "REPOST"
ACTION_PROMOTE = "PROMOTE"


@dataclass
class ActionAdvice:
    """Recommended action for one own listing."""

    fingerprint: str
    title: str
    action: str
    reason: str
    suggested_price: Optional[float] = None
    priority: int = 3  # 1 = urgent … 3 = informational

    def to_dict(self) -> Dict[str, object]:
        return {
            "fingerprint": self.fingerprint,
            "title": self.title,
            "action": self.action,
            "reason": self.reason,
            "suggested_price": self.suggested_price,
            "priority": self.priority,
        }


@dataclass
class NewListingSuggestion:
    """A market gap worth publishing a new listing into."""

    query: str
    reason: str
    suggested_price: Optional[float]
    sample_title: str
    active_competitors: int
    priority: int = 3

    def to_dict(self) -> Dict[str, object]:
        return {
            "query": self.query,
            "reason": self.reason,
            "suggested_price": self.suggested_price,
            "sample_title": self.sample_title,
            "active_competitors": self.active_competitors,
            "priority": self.priority,
        }


class StrategyAdvisor:
    """Combines competitive position + stagnation into portfolio advice."""

    def __init__(self, storage, undercut_alert: int = 2):
        self.storage = storage
        self.watch = CompetitiveWatch(storage)
        self.undercut_alert = undercut_alert

    # ---- Own listings ----

    def advise_actions(
        self,
        min_age_days: float = 3.0,
        min_views_per_day: float = 1.0,
        now: Optional[datetime] = None,
    ) -> List[ActionAdvice]:
        now = now or datetime.now(timezone.utc)
        planner = RepostPlanner(min_age_days=min_age_days, min_views_per_day=min_views_per_day)
        advice: List[ActionAdvice] = []

        for row in self.storage.own_ads(status="active"):
            own = OwnAd(
                title=row["title"],
                price=row["price"],
                currency=row["currency"],
                views=row["last_views"] or 0,
                url=row["url"],
                ad_id=row["ad_id"],
                status=row["status"],
            )
            position = self.watch.price_position(own)
            decision = planner.decide(
                first_seen_at=row["first_seen_at"],
                views_total=row["last_views"] or 0,
                messages_total=row["last_messages"] or 0,
                now=now,
            )
            cheaper = position["cheaper_competitors"]
            median_price = position["median_competitor_price"]

            if cheaper >= self.undercut_alert and own.price and median_price:
                suggested = round(median_price * 0.98)
                advice.append(
                    ActionAdvice(
                        row["fingerprint"],
                        own.title,
                        ACTION_EDIT_PRICE,
                        f"{cheaper} конкурентів дешевші; медіана ніші {median_price:g}. "
                        f"Знизьте до ~{suggested} грн.",
                        suggested_price=suggested,
                        priority=1,
                    )
                )
            elif decision.should_repost:
                advice.append(
                    ActionAdvice(
                        row["fingerprint"],
                        own.title,
                        ACTION_REPOST,
                        decision.reason,
                        priority=2,
                    )
                )
            elif cheaper >= 1 and own.price and median_price and own.price > median_price * 1.1:
                advice.append(
                    ActionAdvice(
                        row["fingerprint"],
                        own.title,
                        ACTION_EDIT_PRICE,
                        f"Ціна вища за медіану ніші ({median_price:g}) — "
                        "перегляди просідатимуть.",
                        suggested_price=round(median_price * 0.98),
                        priority=2,
                    )
                )
            elif (row["last_views"] or 0) < 10 and position["of"] > 5:
                advice.append(
                    ActionAdvice(
                        row["fingerprint"],
                        own.title,
                        ACTION_PROMOTE,
                        f"Ніша конкурентна ({position['of']} схожих), переглядів мало — "
                        "розгляньте офіційне просування або покращіть заголовок/фото.",
                        priority=2,
                    )
                )
            else:
                advice.append(
                    ActionAdvice(
                        row["fingerprint"],
                        own.title,
                        ACTION_KEEP,
                        "Позиція у нормі; періодично оновлюйте снапшот статистики.",
                        priority=3,
                    )
                )

        advice.sort(key=lambda item: item.priority)
        return advice

    # ---- New listings ----

    def advise_new_listings(self, top_n: int = 5) -> List[NewListingSuggestion]:
        """Active market queries not covered by the current portfolio."""
        own_tokens = set()
        for row in self.storage.own_ads():
            own_tokens.update(derive_query(row["title"]).split())

        by_query: Dict[str, list] = {}
        for ad in self.storage.get_ads(active_only=True):
            if ad.query:
                by_query.setdefault(ad.query, []).append(ad)

        suggestions: List[NewListingSuggestion] = []
        for query, ads in by_query.items():
            query_tokens = set(query.lower().split())
            if own_tokens & query_tokens:
                continue  # niche already covered by the portfolio
            prices = [ad.price for ad in ads if ad.price is not None]
            keywords = RecommendationEngine._title_keywords(ads, None)
            recency = sum(1 for ad in ads if ad.published_at and "T" in ad.published_at)
            priority = 1 if len(ads) >= 10 else (2 if len(ads) >= 5 else 3)
            suggestions.append(
                NewListingSuggestion(
                    query=query,
                    reason=(
                        f"Активна ніша: {len(ads)} оголошень у базі, "
                        f"своїх оголошень немає. Ринок живий — варто розміститись."
                    ),
                    suggested_price=round(median(prices) * 0.97) if prices else None,
                    sample_title=" ".join(keywords[:4]).title() or query.title(),
                    active_competitors=len(ads),
                    priority=priority,
                )
            )

        suggestions.sort(key=lambda item: (-item.active_competitors, item.priority))
        return suggestions[:top_n]
