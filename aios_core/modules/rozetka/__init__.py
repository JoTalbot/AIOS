"""Rozetka.ua marketplace agent — full agent with price tracker, autowatch, favorites, auto-login.

Rozetka — крупнейший украинский e-commerce marketplace (электроника,
бытовая техника, автозапчасти). Full agent with Storage, Messenger,
Bootstrap, Collector, CardParser, DetailParser, PriceTracker,
AutoWatch, Favorites, AutoLogin.

Quick start::

    from aios_core.modules.rozetka import RozetkaCollector, RozetkaStorage, RozetkaPriceTracker

    collector = RozetkaCollector()
    with RozetkaStorage("rozetka.sqlite") as storage:
        summary = collector.collect_to_storage(storage, query="iPhone 16")
        tracker = RozetkaPriceTracker(storage)
        drops = tracker.detect_drops()
"""
from .auto_login import RozetkaAutoLogin, LoginState, LoginResult
from .autowatch import RozetkaAutoWatch
from .bootstrap import RozetkaBootstrap
from .card_parser import RozetkaCardParser
from .collector import RozetkaCollector
from .detail import RozetkaDetailParser
from .favorites import RozetkaFavorites
from .messenger import RozetkaMessenger
from .price_tracker import RozetkaPriceTracker, PriceDropAlert
from .storage import RozetkaStorage

__all__ = [
    "LoginResult",
    "LoginState",
    "PriceDropAlert",
    "RozetkaAutoLogin",
    "RozetkaAutoWatch",
    "RozetkaBootstrap",
    "RozetkaCardParser",
    "RozetkaCollector",
    "RozetkaDetailParser",
    "RozetkaFavorites",
    "RozetkaMessenger",
    "RozetkaPriceTracker",
    "RozetkaStorage",
]
