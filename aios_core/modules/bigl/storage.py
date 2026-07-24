"""Bigl storage — наследник OLXStorage с общей схемой объявлений."""

from aios_core.modules.olx.storage import OLXStorage


class BiglStorage(OLXStorage):
    """Хранилище платформы bigl: общая схема ads/price-history/outbox/...."""

