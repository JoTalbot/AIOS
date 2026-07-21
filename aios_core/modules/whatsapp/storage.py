"""WhatsApp storage — наследник OLXStorage (общая схема outbox/chats)."""

from aios_core.modules.olx.storage import OLXStorage


class WhatsAppStorage(OLXStorage):
    """Хранилище платформы whatsapp: таблицы outbox/seen/own_ads общие."""

    pass
