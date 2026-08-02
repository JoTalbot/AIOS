"""Тесты для aios_core/security/security_policy.py (pydantic v2).

Закрывает 3 дублирующихся backlog-пункта «добавить тесты для security_policy.py».
Покрывает: конфиг (defaults + валидаторы), XSS/JS-санитайзеры, жизненный цикл
CSRF-токенов (one-time, expiry), валидацию заголовков, cookie-атрибуты и
сканер hard-coded secrets.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aios_core.security.security_policy import (  # noqa: E402
    CSRFTokenData,
    SecurityPolicy,
    SecurityPolicyConfig,
    security_policy_config,
)

XSS_PAYLOAD = "<script>alert('XSS')</script>"


@pytest.fixture(autouse=True)
def clean_csrf_tokens():
    """Изоляция: _csrf_tokens — class-level dict, чистим между тестами."""
    SecurityPolicy._csrf_tokens.clear()
    yield
    SecurityPolicy._csrf_tokens.clear()


# ---------- конфиг ----------

class TestConfigDefaults:
    def test_default_secret_key_strong(self):
        assert len(security_policy_config.secret_key) >= 32

    def test_default_csrf_expiry_30(self):
        assert security_policy_config.csrf_token_expiry_minutes == 30

    def test_default_cookie_flags(self):
        assert security_policy_config.session_cookie_secure is True
        assert security_policy_config.session_cookie_httponly is True
        assert security_policy_config.session_cookie_samesite == "Lax"


class TestConfigValidation:
    def test_short_secret_rejected(self):
        with pytest.raises(ValidationError):
            SecurityPolicyConfig(secret_key="short")

    def test_too_long_secret_rejected(self):
        with pytest.raises(ValidationError):
            SecurityPolicyConfig(secret_key="x" * 129)

    def test_csrf_expiry_bounds(self):
        with pytest.raises(ValidationError):
            SecurityPolicyConfig(csrf_token_expiry_minutes=0)
        with pytest.raises(ValidationError):
            SecurityPolicyConfig(csrf_token_expiry_minutes=1441)

    def test_samesite_pattern(self):
        SecurityPolicyConfig(session_cookie_samesite="Strict")
        SecurityPolicyConfig(session_cookie_samesite="None")
        with pytest.raises(ValidationError):
            SecurityPolicyConfig(session_cookie_samesite="strict-lower")
        with pytest.raises(ValidationError):
            SecurityPolicyConfig(session_cookie_samesite="bogus")


# ---------- XSS/JS санитайзеры ----------

class TestSanitizeInput:
    def test_xss_escaped(self):
        out = SecurityPolicy.sanitize_input(XSS_PAYLOAD)
        assert "<script>" not in out
        assert "&lt;script&gt;" in out

    def test_non_str_raises(self):
        for bad in (None, 42, ["x"]):
            with pytest.raises(ValueError):
                SecurityPolicy.sanitize_input(bad)  # type: ignore[arg-type]

    def test_empty_returns_empty(self):
        assert SecurityPolicy.sanitize_input("") == ""
        assert SecurityPolicy.sanitize_input("   ") == ""

    def test_plain_text_passthrough(self):
        assert SecurityPolicy.sanitize_input("hello world") == "hello world"


class TestSanitizeJsInput:
    def test_quotes_and_backslash_escaped(self):
        out = SecurityPolicy.sanitize_js_input('a"b\'c\\d')
        assert '\\"' in out
        assert "\\'" in out
        assert "\\\\" in out

    def test_non_str_raises(self):
        with pytest.raises(ValueError):
            SecurityPolicy.sanitize_js_input(None)  # type: ignore[arg-type]


# ---------- CSRF токены ----------

class TestCsrfTokens:
    def test_generate_returns_strong_token(self):
        token = SecurityPolicy.generate_csrf_token()
        assert isinstance(token, str) and len(token) >= 32
        assert token in SecurityPolicy._csrf_tokens

    def test_valid_token_passes_once(self):
        token = SecurityPolicy.generate_csrf_token()
        assert SecurityPolicy.validate_csrf_token(token) is True
        # one-time: токен удалён после успешной валидации
        assert SecurityPolicy.validate_csrf_token(token) is False

    def test_unknown_token_rejected(self):
        assert SecurityPolicy.validate_csrf_token("x" * 40) is False

    def test_empty_token_rejected(self):
        assert SecurityPolicy.validate_csrf_token("") is False
        assert SecurityPolicy.validate_csrf_token("   ") is False

    def test_non_str_raises(self):
        with pytest.raises(ValueError):
            SecurityPolicy.validate_csrf_token(None)  # type: ignore[arg-type]

    def test_expired_token_rejected_and_evicted(self):
        token = SecurityPolicy.generate_csrf_token()
        SecurityPolicy._csrf_tokens[token] = datetime.now() - timedelta(minutes=1)
        assert SecurityPolicy.validate_csrf_token(token) is False
        assert token not in SecurityPolicy._csrf_tokens


class TestCsrfTokenData:
    def test_valid_model(self):
        d = CSRFTokenData(token="t" * 40, expiry=datetime.now())
        assert d.token == "t" * 40

    def test_short_token_rejected(self):
        with pytest.raises(ValidationError):
            CSRFTokenData(token="short", expiry=datetime.now())


# ---------- заголовки / cookies / secrets-сканер ----------

class TestRequestHeaders:
    def test_no_origin_no_referer_ok(self):
        assert SecurityPolicy.validate_request_headers({}) is True

    def test_allowed_origin_ok(self):
        headers = {"Origin": "https://app.example.com"}
        assert SecurityPolicy.validate_request_headers(headers, ["app.example.com"]) is True

    def test_evil_origin_rejected(self):
        headers = {"Origin": "https://evil.example.com"}
        assert SecurityPolicy.validate_request_headers(headers, ["app.example.com"]) is False

    def test_evil_referer_rejected(self):
        headers = {"Referer": "https://evil.example.com/page"}
        assert SecurityPolicy.validate_request_headers(headers, ["app.example.com"]) is False


class TestSessionCookieAttributes:
    def test_flags_match_config(self):
        attrs = SecurityPolicy.get_session_cookie_attributes()
        assert attrs == {
            "secure": security_policy_config.session_cookie_secure,
            "httponly": security_policy_config.session_cookie_httponly,
            "samesite": security_policy_config.session_cookie_samesite,
        }


class TestHardcodedSecretsScanner:
    def test_detects_secret(self, tmp_path):
        f = tmp_path / "leak.py"
        f.write_text("api_key = 'AKIA" + "x" * 30 + "'\n", encoding="utf-8")
        assert SecurityPolicy.check_for_hardcoded_secrets(str(f))

    def test_clean_file_empty(self, tmp_path):
        f = tmp_path / "clean.py"
        f.write_text("x = 1\n", encoding="utf-8")
        assert SecurityPolicy.check_for_hardcoded_secrets(str(f)) == []

    def test_missing_file_returns_empty(self):
        assert SecurityPolicy.check_for_hardcoded_secrets("/nonexistent/nope.py") == []
