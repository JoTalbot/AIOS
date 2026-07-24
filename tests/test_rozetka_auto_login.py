"""Tests for Rozetka.ua auto-login scaffold."""

from __future__ import annotations

from aios_core.modules.rozetka.auto_login import (
    RozetkaAutoLogin,
    LoginState,
    LoginResult,
)


def test_login_state_values():
    """All LoginState enum values are present."""
    states = list(LoginState)
    assert len(states) == 8
    assert LoginState.NOT_STARTED.value == "not_started"
    assert LoginState.LOGIN_SUCCESS.value == "login_success"
    assert LoginState.CAPTCHA_REQUIRED.value == "captcha_required"
    assert LoginState.TWO_FA_REQUIRED.value == "two_fa_required"


def test_login_result_defaults():
    """LoginResult has sensible defaults."""
    result = LoginResult()
    assert result.state == LoginState.NOT_STARTED
    assert result.message == ""
    assert result.session_id is None
    assert result.retry_count == 0


def test_detect_login_screen_empty():
    """Empty XML dump returns NOT_STARTED."""
    auto = RozetkaAutoLogin()
    state = auto.detect_login_screen("")
    assert state == LoginState.NOT_STARTED


def test_detect_login_screen_with_markers():
    """XML with login markers returns LOGIN_SCREEN_FOUND."""
    auto = RozetkaAutoLogin()
    xml = '<node resource-id="login_button" text="Увійти" />'
    state = auto.detect_login_screen(xml)
    assert state == LoginState.LOGIN_SCREEN_FOUND


def test_detect_login_screen_already_logged_in():
    """XML with profile but no login markers returns LOGIN_SUCCESS."""
    auto = RozetkaAutoLogin()
    xml = '<node resource-id="profile_section" text="Мій профіль" />'
    state = auto.detect_login_screen(xml)
    assert state == LoginState.LOGIN_SUCCESS


def test_detect_login_screen_no_markers():
    """XML without login markers returns APP_OPENED."""
    auto = RozetkaAutoLogin()
    xml = '<node resource-id="product_list" text="Товари" />'
    state = auto.detect_login_screen(xml)
    assert state == LoginState.APP_OPENED


def test_attempt_login_no_credentials():
    """Attempt login without credentials returns appropriate message."""
    auto = RozetkaAutoLogin()
    result = auto.attempt_login(
        email=None,
        password=None,
        xml_dump='<node resource-id="login_button" />',
    )
    assert result.state in (LoginState.LOGIN_SCREEN_FOUND, LoginState.CREDENTIALS_ENTERED)


def test_attempt_login_with_captcha():
    """Login attempt with captcha returns CAPTCHA_REQUIRED."""
    auto = RozetkaAutoLogin()
    xml = '<node resource-id="login_button" /><node resource-id="captcha_image" />'
    result = auto.attempt_login(email="test@test.com", password="pass", xml_dump=xml)
    assert result.state == LoginState.CAPTCHA_REQUIRED
    assert "Captcha" in result.message


def test_attempt_login_with_2fa():
    """Login attempt with 2FA returns TWO_FA_REQUIRED."""
    auto = RozetkaAutoLogin()
    xml = '<node resource-id="login_button" /><node resource-id="otp_input" />'
    result = auto.attempt_login(email="test@test.com", password="pass", xml_dump=xml)
    assert result.state == LoginState.TWO_FA_REQUIRED
    assert "2FA" in result.message


def test_login_result_to_dict_via_state():
    """LoginResult state serializes properly."""
    result = LoginResult(state=LoginState.CREDENTIALS_ENTERED, message="creds entered")
    assert result.state.value == "credentials_entered"
    assert result.message == "creds entered"
