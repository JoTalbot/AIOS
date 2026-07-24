"""Rozetka messenger — approval-gated outbox scaffold.

Rozetka использует чат продавца через UI приложения (com.rozetka).
Мессенджер наследует OLXMessenger pattern с approval-outbox.
"""

from aios_core.modules.olx.messenger import OLXMessenger


class RozetkaMessenger(OLXMessenger):
    """Мессенджер для rozetka.ua: approval-gated outbox.

    PACKAGE = "com.rozetka"
    DEEP_LINK = "rozetka://chats"
    """

    PACKAGE = "com.rozetka"
    DEEP_LINK = "rozetka://chats"
