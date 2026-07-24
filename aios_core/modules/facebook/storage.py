"""Facebook storage — наследник OLXStorage (общая схема outbox/chats/seen)."""

from aios_core.modules.olx.storage import OLXStorage


class FacebookStorage(OLXStorage):
    """Хранилище платформы facebook: таблицы outbox/seen/own_ads общие."""

