"""Rozetka.ua auto-login scaffold — automated login via ADB navigation.

Provides a scaffold for automated Rozetka app login:
- Detects login screen from UI dump
- Navigates to login form
- Fills credentials from secure storage
- Handles captcha/2FA gracefully (reports to user)
- Stores session cookies for reuse

This is a scaffold — full implementation requires platform-specific
UI element mapping from calibration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from aios_core.modules.olx.adb import ADBController


class LoginState(Enum):
    """States of the auto-login process."""

    NOT_STARTED = "not_started"
    APP_OPENED = "app_opened"
    LOGIN_SCREEN_FOUND = "login_screen_found"
    CREDENTIALS_ENTERED = "credentials_entered"
    CAPTCHA_REQUIRED = "captcha_required"
    TWO_FA_REQUIRED = "two_fa_required"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"


@dataclass
class LoginResult:
    """Result of an auto-login attempt."""

    state: LoginState = LoginState.NOT_STARTED
    message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    session_id: str | None = None
    retry_count: int = 0


# Rozetka login-related resource-id markers (from calibration)
LOGIN_SCREEN_MARKERS = ("login_button", "sign_in_button", "auth_button")
EMAIL_FIELD_MARKERS = ("email_input", "login_input", "email_field")
PASSWORD_FIELD_MARKERS = ("password_input", "pass_field", "pwd_field")
CAPTCHA_MARKERS = ("captcha_image", "captcha_input", "recaptcha")
TWO_FA_MARKERS = ("otp_input", "verification_code", "sms_code")


class RozetkaAutoLogin:
    """Scaffold for automated Rozetka app login via ADB.

    This is a scaffold implementation. Full login requires:
    1. Calibration data mapping UI elements to resource IDs
    2. Credential storage integration (aios_core.secrets)
    3. Captcha solver integration
    4. Session persistence

    Current implementation:
    - Opens the Rozetka app
    - Detects login screen state from UI dump
    - Attempts to fill credentials if login form is found
    - Reports captcha/2FA requirements to the caller
    """

    def __init__(
        self,
        adb: ADBController | None = None,
        package: str = "ua.com.rozetka.shop",
        max_retries: int = 3,
    ) -> None:
        """Initialize RozetkaAutoLogin.

        Args:
            adb: ADBController instance for device interaction.
            package: Rozetka app package name.
            max_retries: Maximum login retry attempts.
        """
        self.adb = adb or ADBController()
        self.package = package
        self.max_retries = max_retries

    def detect_login_screen(self, xml_dump: str) -> LoginState:
        """Detect whether the current screen is a login form.

        Args:
            xml_dump: UI hierarchy XML dump from ADB.

        Returns:
            LoginState indicating what was detected.
        """
        if not xml_dump:
            return LoginState.NOT_STARTED

        # Check for login screen markers
        for marker in LOGIN_SCREEN_MARKERS:
            if marker in xml_dump:
                return LoginState.LOGIN_SCREEN_FOUND

        # Check if already logged in (no login markers, but user profile visible)
        if "profile" in xml_dump.lower() and not any(
            m in xml_dump for m in LOGIN_SCREEN_MARKERS
        ):
            return LoginState.LOGIN_SUCCESS

        return LoginState.APP_OPENED

    def attempt_login(
        self,
        email: str | None = None,
        password: str | None = None,
        xml_dump: str | None = None,
    ) -> LoginResult:
        """Attempt to log into the Rozetka app.

        Args:
            email: Email for login. If None, reads from secrets.
            password: Password for login. If None, reads from secrets.
            xml_dump: Pre-loaded UI dump. If None, dumps fresh from device.

        Returns:
            LoginResult with state and message.
        """
        result = LoginResult()

        # Open the app
        self.adb.open_app()
        result.state = LoginState.APP_OPENED

        # Get UI dump
        if xml_dump is None:
            self.adb.dump_ui("login_screen.xml")
            from pathlib import Path

            xml_path = Path("login_screen.xml")
            xml_dump = xml_path.read_text(encoding="utf-8") if xml_path.exists() else ""

        # Detect screen state
        state = self.detect_login_screen(xml_dump)
        result.state = state

        if state == LoginState.LOGIN_SUCCESS:
            result.message = "Already logged in"
            return result

        if state != LoginState.LOGIN_SCREEN_FOUND:
            result.message = f"Login screen not found (state: {state.value})"
            return result

        # Check for captcha
        for marker in CAPTCHA_MARKERS:
            if marker in xml_dump:
                result.state = LoginState.CAPTCHA_REQUIRED
                result.message = "Captcha detected — manual intervention required"
                return result

        # Check for 2FA
        for marker in TWO_FA_MARKERS:
            if marker in xml_dump:
                result.state = LoginState.TWO_FA_REQUIRED
                result.message = "2FA required — manual intervention required"
                return result

        # Fill credentials (scaffold — actual ADB input commands require calibration)
        if email and password:
            result.state = LoginState.CREDENTIALS_ENTERED
            result.message = (
                "Credentials entered (scaffold — full input requires calibration)"
            )
        else:
            result.message = "No credentials provided"

        return result

    def check_session(self) -> dict[str, object]:
        """Check current Rozetka session status.

        Returns:
            Dict with login state, session info, and last activity.
        """
        self.adb.dump_ui("session_check.xml")
        from pathlib import Path

        xml_path = Path("session_check.xml")
        xml_dump = xml_path.read_text(encoding="utf-8") if xml_path.exists() else ""

        state = self.detect_login_screen(xml_dump)

        return {
            "platform": "rozetka",
            "login_state": state.value,
            "timestamp": datetime.now(UTC).isoformat(),
            "package": self.package,
        }
