"""Rozetka storage — наследник OLXStorage с общей схемой товаров."""

from aios_core.modules.olx.storage import OLXStorage


class RozetkaStorage(OLXStorage):
    """Хранилище платформы rozetka: общая схема ads/price-history/outbox/....

    Rozetka использует ту же схему объявлений (товаров) как OLX,
    с расширениями для отзывов, сравнения цен и автозапчастей.
    """

