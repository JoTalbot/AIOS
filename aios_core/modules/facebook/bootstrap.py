"""Facebook Marketplace bootstrap — doctor через generic platform_doctor."""

from __future__ import annotations

from aios_core.platforms.doctor import platform_doctor

from .storage import FacebookStorage

PLATFORM = "facebook"
PACKAGE = "com.facebook.katana"


class FacebookBootstrap:
    """Смотритель готовности facebook (OLX-like платформа полного стека)."""

    def __init__(self, adb=None, serial=None, directory: str = "platforms", which=None):
        """Initialize FacebookBootstrap."""
        self.adb = adb
        self.serial = serial
        self.directory = directory
        self.which = which

    def doctor(self) -> None:
        """Run readiness checks for this platform agent."""
        return platform_doctor(
            PLATFORM,
            PACKAGE,
            adb=self.adb,
            serial=self.serial,
            directory=self.directory,
            which=self.which,
            required_hints=("cards", "messenger"),
            storage_factory=lambda: FacebookStorage(":memory:"),
        )
