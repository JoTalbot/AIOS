"""WhatsApp bootstrap — doctor через generic platform_doctor."""

from __future__ import annotations

from aios_core.platforms.doctor import platform_doctor

from .storage import WhatsAppStorage

PLATFORM = "whatsapp"
PACKAGE = "com.whatsapp"


class WhatsAppBootstrap:
    """Смотритель готовности whatsapp (messenger-first платформа)."""

    def __init__(self, adb=None, serial=None, directory: str = "platforms", which=None):
        self.adb = adb
        self.serial = serial
        self.directory = directory
        self.which = which

    def doctor(self):
        return platform_doctor(
            PLATFORM,
            PACKAGE,
            adb=self.adb,
            serial=self.serial,
            directory=self.directory,
            which=self.which,
            required_hints=("messenger",),
            storage_factory=lambda: WhatsAppStorage(":memory:"),
        )
