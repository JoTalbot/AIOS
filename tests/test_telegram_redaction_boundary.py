from __future__ import annotations

import requests

from tg_bot.api import TelegramAPI, TelegramTransportError
from tg_bot.redaction import redact_runtime_text


def test_redactor_removes_bot_token_bearer_query_and_chat_metadata():
    token = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
    value = (
        f"POST https://api.telegram.org/bot{token}/sendMessage?token={token} "
        f"Authorization: Bearer {token} chat=-1001234567890"
    )
    clean = redact_runtime_text(value)
    assert token not in clean
    assert "-1001234567890" not in clean
    assert "token=[redacted]" in clean


def test_api_transport_exception_never_contains_credential_url(monkeypatch):
    token = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"

    def fail(url, **_kwargs):
        raise requests.ConnectionError(f"failed URL {url}")

    monkeypatch.setattr(requests, "post", fail)
    api = TelegramAPI(token)
    try:
        api.get_me()
    except TelegramTransportError as exc:
        assert token not in str(exc)
        assert "api.telegram.org" not in str(exc)
    else:
        raise AssertionError("transport failure must be wrapped")
