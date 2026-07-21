"""AIOS OLX Android Agent — AutoWatch: the full unattended care cycle.

One cycle:

1. collect the subscribed search queries (new ads → subscription alerts);
2. snapshot own listings (via an injectable provider or the device);
3. detect stagnant own ads;
4. generate improvement suggestions and repost decisions for them;
5. send configured notifications (subscription hits, favorite price drops,
   stagnant listings).

Every stage is optional and injectable, so the loop is fully testable
without a device. Sending messages and executing reposts stay guarded by
their own latches (outbox approval, ``confirm=True``) — AutoWatch only
*prepares* drafts and plans.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from .collector import OLXCollector
from .notifier import WebhookNotifier, notify_stagnant
from .own_ads import OwnAd, OwnAdsTracker
from .promotion import AdImprover, RepostPlanner, Reposter
from .scheduler import CollectionScheduler
from .watch import FavoritesWatch, SubscriptionManager


class AutoWatch:
    """Orchestrates one full care cycle over OLX data."""

    def __init__(
        self,
        storage,
        collector: Optional[OLXCollector] = None,
        own_provider: Optional[Callable[[], List[OwnAd]]] = None,
        notifier: Optional[WebhookNotifier] = None,
        max_cards: int = 50,
    ):
        self.storage = storage
        self.collector = collector
        self.own_provider = own_provider
        self.notifier = notifier or WebhookNotifier(url=None)
        self.max_cards = max_cards

    def run_cycle(
        self,
        queries: Optional[List[str]] = None,
        collect: bool = True,
        min_age_days: float = 3.0,
        min_views_per_day: float = 1.0,
    ) -> Dict[str, object]:
        report: Dict[str, object] = {}

        # 1. Collection + subscription alerts
        new_cards: List = []
        if collect and queries and self.collector is not None:
            scheduler = CollectionScheduler(
                collector=self.collector, storage=self.storage
            )
            collection = scheduler.run_once(queries, max_cards=self.max_cards)
            report["collection"] = collection

            # "New" cards = fingerprint has exactly one sighting (first seen
            # during this cycle).
            for query in queries:
                for card in self.storage.get_ads(query=query):
                    history = self.storage.price_history(card.fingerprint)
                    if len(history) == 1:
                        new_cards.append(card)
            report["subscription_alerts"] = SubscriptionManager(
                self.storage
            ).check_new(new_cards)
            report["favorite_alerts"] = FavoritesWatch(self.storage).price_alerts()
        else:
            report["subscription_alerts"] = []
            report["favorite_alerts"] = []

        # 2. Own listings snapshot
        tracker = OwnAdsTracker(self.storage)
        if self.own_provider is not None:
            own_ads = self.own_provider()
            report["own_snapshot"] = tracker.record_snapshot(own_ads)
        else:
            report["own_snapshot"] = None

        # 3–4. Stagnant detection + improvement & repost planning
        stagnant = tracker.stagnant(
            min_age_days=min_age_days, min_views_per_day=min_views_per_day
        )
        report["stagnant"] = stagnant

        improver = AdImprover()
        planner = RepostPlanner(
            min_age_days=min_age_days, min_views_per_day=min_views_per_day
        )
        competitors = self.storage.get_ads()

        suggestions: List[Dict[str, object]] = []
        decisions: List[Dict[str, object]] = []
        rows = {row["fingerprint"]: row for row in self.storage.own_ads(status="active")}
        for item in stagnant:
            row = rows.get(item["fingerprint"])
            if row is None:
                continue
            own_ad = OwnAd(
                title=row["title"], price=row["price"], currency=row["currency"],
                views=row["last_views"] or 0, url=row["url"], ad_id=row["ad_id"],
                status=row["status"],
            )
            suggestion = improver.improve(own_ad, competitors)
            decision = planner.decide(
                first_seen_at=row["first_seen_at"],
                views_total=row["last_views"] or 0,
                messages_total=row["last_messages"] or 0,
            )
            plan = (
                Reposter().plan_steps(own_ad, suggestion)
                if decision.should_repost
                else []
            )
            suggestions.append(suggestion.to_dict())
            decisions.append(
                {
                    **decision.to_dict(),
                    "fingerprint": row["fingerprint"],
                    "title": row["title"],
                    "plan": plan,
                }
            )
        report["suggestions"] = suggestions
        report["repost_decisions"] = decisions

        # 4b. Competitive surveillance driven by own listings
        if rows:
            from .competitive import CompetitiveWatch
            from .advisor import StrategyAdvisor
            own_list = [
                OwnAd(
                    title=row["title"], price=row["price"], currency=row["currency"],
                    views=row["last_views"] or 0, url=row["url"],
                    ad_id=row["ad_id"], status=row["status"],
                )
                for row in rows.values()
            ]
            report["competitive"] = CompetitiveWatch(self.storage).refresh(own_list)
            report["advisor"] = [
                item.to_dict()
                for item in StrategyAdvisor(self.storage).advise_actions()
            ]
        else:
            report["competitive"] = None
            report["advisor"] = []

        # 5. Notifications (no-op without a configured webhook)
        sent = 0
        for alert in report["subscription_alerts"]:
            sent += int(self.notifier.send("olx_subscription_new_ads", alert))
        for alert in report["favorite_alerts"]:
            sent += int(self.notifier.send("olx_favorite_price_drop", alert))
        stagnant_summary = notify_stagnant(stagnant, self.notifier)
        sent += stagnant_summary["sent"]
        report["notifications_sent"] = sent

        return report
