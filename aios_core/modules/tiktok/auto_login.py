"""TikTok auto-login scaffold — inherits RozetkaAutoLogin with TikTok package."""

from aios_core.modules.rozetka.auto_login import RozetkaAutoLogin


PACKAGE = "com.zhiliaoapp.musically"

# TikTok login-specific markers
TIKTOK_LOGIN_MARKERS = ("login_button", "sign_up", "email_login", "phone_login")
TIKTOK_CAPTCHA_MARKERS = ("captcha", "verification", "rotate_captcha", "puzzle_captcha")


class TikTokAutoLogin(RozetkaAutoLogin):
    """Auto-login scaffold for TikTok.

    Inherits RozetkaAutoLogin with TikTok-specific package and markers.
    TikTok has unique captcha types (rotate/puzzle) that require
    manual intervention.
    """

    def __init__(self, adb=None, package: str = PACKAGE, max_retries: int = 3) -> None:
        """Initialize TikTokAutoLogin."""
        super().__init__(adb=adb, package=package, max_retries=max_retries)
