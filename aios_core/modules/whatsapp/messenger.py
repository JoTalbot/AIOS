"""WhatsApp Messenger — guarded-обёртка HintsMessenger.

Guarded-контур общий: ответы по умолчанию только в outbox-очередь,
на устройство — после flush/auto_send. Platform-specific — только
package, deep-link инбокса и имя платформы для hints.
"""

from __future__ import annotations

from aios_core.platforms.hintmsg import HintsMessenger

PACKAGE = "com.whatsapp"
DEEP_LINK = 'whatsapp://'


class WhatsAppMessenger(HintsMessenger):
    """WhatsApp messenger по calibrated hints (parser_hints.messenger)."""

    PACKAGE = PACKAGE
    DEEP_LINK = DEEP_LINK

    def __init__(self, adb=None, storage=None, messenger_hints=None,
                 directory: str = "platforms", screen_width: int = 1080,
                 serial=None):
        super().__init__(
            platform="whatsapp", package=PACKAGE, deep_link=DEEP_LINK,
            adb=adb, storage=storage, messenger_hints=messenger_hints,
            directory=directory, screen_width=screen_width, serial=serial,
        )
