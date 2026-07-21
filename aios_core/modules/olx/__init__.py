"""AIOS OLX Android Agent.

Turns the OLX Ukraine Android app (``ua.slando``) into a structured data
source: ADB device control, UIAutomator dump parsing, automated scrolling
collection, SQLite persistence, competitor analysis and listing
recommendations.

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
    Recommendation,
    RecommendationEngine,
)
from .card_parser import CardParser
from .collector import OLXCollector
from .models import AdCard
from .storage import OLXStorage
from .ui_parser import UIParser

__all__ = [
    "ADBController",
    "AdCard",
    "CardParser",
    "CompetitorAnalyzer",
    "CompetitorReport",
    "OLXCollector",
    "OLXStorage",
    "Recommendation",
    "RecommendationEngine",
    "UIParser",
]
