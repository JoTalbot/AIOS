"""Facebook auto-login scaffold — inherits RozetkaAutoLogin with FB package."""

from aios_core.modules.rozetka.auto_login import RozetkaAutoLogin

PACKAGE = "com.facebook.katana"

# Facebook login-specific markers
FB_LOGIN_MARKERS = ("login_button", "email_field", "password_field", "sign_in")


class FacebookAutoLogin(RozetkaAutoLogin):
    """Auto-login scaffold for Facebook.

    Inherits RozetkaAutoLogin with Facebook-specific package and markers.
    """

    def __init__(self, adb=None, package: str = PACKAGE, max_retries: int = 3) -> None:
        """Initialize FacebookAutoLogin."""
        super().__init__(adb=adb, package=package, max_retries=max_retries)
