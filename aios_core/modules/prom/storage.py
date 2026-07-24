"""Prom storage — наследник OLXStorage с общей схемой объявлений."""

from aios_core.modules.olx.storage import OLXStorage


class PromStorage(OLXStorage):
    """Хранилище платформы prom: общая схема ads/price-history/outbox/...."""

