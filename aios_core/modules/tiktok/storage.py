"""TikTok storage — наследник OLXStorage (общая схема outbox/chats)."""

from aios_core.modules.olx.storage import OLXStorage


class TikTokStorage(OLXStorage):
    """Хранилище платформы tiktok: таблицы outbox/seen/own_ads общие."""

    pass
