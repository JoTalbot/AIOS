"""Viber storage — наследник OLXStorage (общая схема outbox/chats)."""

from aios_core.modules.olx.storage import OLXStorage


class ViberStorage(OLXStorage):
    """Хранилище платформы viber: таблицы outbox/seen/own_ads общие."""

