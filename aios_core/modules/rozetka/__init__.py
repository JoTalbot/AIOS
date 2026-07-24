"""Rozetka.ua marketplace agent — scaffold with collector, card_parser, detail.

Rozetka — крупнейший украинский e-commerce marketplace (электроника,
бытовая техника, автозапчасти). Full agent with Storage, Messenger,
Bootstrap, Collector, CardParser, DetailParser.

Quick start::

    from aios_core.modules.rozetka import RozetkaCollector, RozetkaStorage

    collector = RozetkaCollector()
    with RozetkaStorage("rozetka.sqlite") as storage:
        summary = collector.collect_to_storage(storage, query="iPhone 16")
"""
from .bootstrap import RozetkaBootstrap
from .card_parser import RozetkaCardParser
from .collector import RozetkaCollector
from .detail import RozetkaDetailParser
from .messenger import RozetkaMessenger
from .storage import RozetkaStorage

__all__ = [
    "RozetkaBootstrap",
    "RozetkaCardParser",
    "RozetkaCollector",
    "RozetkaDetailParser",
    "RozetkaMessenger",
    "RozetkaStorage",
]
