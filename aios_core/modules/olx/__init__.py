"""AIOS OLX Android Agent.

Turns the Slando Ukraine Android app (``ua.slando``) into a structured data
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
from .advisor import (
    ACTION_EDIT_CONTENT,
    ACTION_EDIT_PRICE,
    ACTION_KEEP,
    ACTION_PROMOTE,
    ACTION_REPOST,
    ActionAdvice,
    NewListingSuggestion,
    StrategyAdvisor,
)
from .analytics import (
    CompetitorAnalyzer,
    CompetitorReport,
    PriceChange,
    PriceTracker,
    Recommendation,
    RecommendationEngine,
)
from .autowatch import AutoWatch
from .bootstrap import OLXBootstrap
from .card_parser import CardParser
from .collector import OLXCollector
from .competitive import (
    CompetitiveWatch,
    derive_query,
    link_score,
    parse_seller_ads,
    title_similarity,
)
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
    OwnAdEditor,
    RepostDecision,
    RepostPlanner,
    Reposter,
)
from .profile import ProfileEditor, ProfileInfo, ProfileParser, SettingsInfo
from .scheduler import CollectionScheduler
from .storage import OLXStorage
from .ui_parser import UIParser
from .watch import FavoritesWatch, SubscriptionManager

__all__ = [
    "ACTION_EDIT_CONTENT",
    "ACTION_EDIT_PRICE",
    "ACTION_KEEP",
    "ACTION_PROMOTE",
    "ACTION_REPOST",
    "ADBController",
    "ActionAdvice",
    "AdCard",
    "AdDetail",
    "AdDetailParser",
    "AdImprover",
    "AutoWatch",
    "CardParser",
    "ChatListParser",
    "ChatThread",
    "ChatViewParser",
    "CollectionScheduler",
    "CompetitiveWatch",
    "CompetitorAnalyzer",
    "CompetitorReport",
    "FavoritesWatch",
    "ImprovementSuggestion",
    "Message",
    "NewListingSuggestion",
    "OLXBootstrap",
    "OLXCollector",
    "OLXMessenger",
    "OLXStorage",
    "OwnAd",
    "OwnAdEditor",
    "OwnAdsParser",
    "OwnAdsTracker",
    "PriceChange",
    "PriceTracker",
    "ProfileEditor",
    "ProfileInfo",
    "ProfileParser",
    "Recommendation",
    "RecommendationEngine",
    "ReplySuggester",
    "RepostDecision",
    "RepostPlanner",
    "Reposter",
    "SettingsInfo",
    "StrategyAdvisor",
    "SubscriptionManager",
    "UIParser",
    "WebhookNotifier",
    "collect_price_drop_alerts",
    "derive_query",
    "link_score",
    "notify_price_drops",
    "notify_stagnant",
    "parse_seller_ads",
    "title_similarity",
]
