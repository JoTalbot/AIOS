"""Rozetka.ua marketplace agent — скелет, сгенерированный scaffold.

Хранилище унаследовано от OLXStorage: схема объявлений (товаров),
история цен, подписки/избранное, outbox, свои товары, конкурентные
связи, kv-профиль.

Rozetka — крупнейший украинский e-commerce marketplace (электроника,
бытовая техника, автозапчасти и др.). Парсеры/коллекторы добавляются
по мере калибровки под UI приложения (com.rozetka).

Quick start::

    from aios_core.modules.rozetka import RozetkaStorage, RozetkaMessenger

    with RozetkaStorage("rozetka.sqlite") as storage:
        storage.save_ads([ProductCard(title="iPhone 16", price=42999)])
        products = storage.get_ads()
"""
from .bootstrap import RozetkaBootstrap
from .messenger import RozetkaMessenger
from .storage import RozetkaStorage

__all__ = ["RozetkaBootstrap", "RozetkaMessenger", "RozetkaStorage"]
