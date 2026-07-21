"""AIOS OLX Android Agent.

Turns the OLX Ukraine Android app (``ua.slando``) into a structured data
source and a guarded action surface: ADB device control, UIAutomator dump
parsing, automated scrolling collection, SQLite persistence with price
history, competitor analysis, recommendations, own-ads monitoring,
improvement & repost planning, personal-chat reading with an approval-gated
reply outbox, and webhook notifications.

Quick start::

    from aios_core.modules.olx import OLXCollector, OLXStorage, RecommendationEngine

    collector = OLXCollector()
    collector.launch_search("лобове скло")
    with OLXStorage("olx_ads.sqlite") as storage:
        summary = collector.collect_to_storage(storage, query="лобове скло", max_cards=50)
        ads = storage.get_ads(query="лобове скло")

    advice = RecommendationEngine().recommend(ads, my_ad=my_draft_card)
    print(advice.to_text())
"""

from .adb import ADBController
from .analytics import (
    CompetitorAnalyzer,
    CompetitorReport,
    PriceChange,
    PriceTracker,
    Recommendation,
    RecommendationEngine,
)
from .card_parser import CardParser
from .collector import OLXCollector
from .detail import AdDetail, AdDetailParser
from .messenger import (
    ChatListParser,
    ChatThread,
    ChatViewParser,
    Message,
    OLXMessenger,
    ReplySuggester,
)
from .models import AdCard
from .notifier import (
    WebhookNotifier,
    collect_price_drop_alerts,
    notify_price_drops,
    notify_stagnant,
)
from .own_ads import OwnAd, OwnAdsParser, OwnAdsTracker
from .promotion import (
    AdImprover,
    ImprovementSuggestion,
    RepostDecision,
    RepostPlanner,
    Reposter,
)
from .scheduler import CollectionScheduler
from .storage import OLXStorage
from .ui_parser import UIParser

__all__ = [
    "ADBController",
    "AdCard",
    "AdDetail",
    "AdDetailParser",
    "AdImprover",
    "CardParser",
    "ChatListParser",
    "ChatThread",
    "ChatViewParser",
    "CollectionScheduler",
    "CompetitorAnalyzer",
    "CompetitorReport",
    "ImprovementSuggestion",
    "Message",
    "OLXCollector",
    "OLXMessenger",
    "OLXStorage",
    "OwnAd",
    "OwnAdsParser",
    "OwnAdsTracker",
    "PriceChange",
    "PriceTracker",
    "Recommendation",
    "RecommendationEngine",
    "ReplySuggester",
    "RepostDecision",
    "RepostPlanner",
    "Reposter",
    "UIParser",
    "WebhookNotifier",
    "collect_price_drop_alerts",
    "notify_price_drops",
    "notify_stagnant",
]
