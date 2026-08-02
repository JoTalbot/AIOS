"""Tests for Telegram account-control dialogue (Google + Instagram)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_telegram_bot as m


class FakeAPI:
    def __init__(self):
        self.messages = []
        self.photos = []

    def send_message(self, chat_id, text, parse_mode="HTML", reply_markup=None, **kw):
        self.messages.append(text)
        return {}

    def send_photo(self, chat_id, path, caption=""):
        self.photos.append((path, caption))
        return {}


def _make_canned():
    return {
        ("google", "whoami"): {"status": "ok", "email": "jo.talbot@gmail.com",
                               "raw": "Аккаунт Google: Jo Talbot (jo.talbot@gmail.com)"},
        ("google", "gmail_list", "5"): {"status": "ok", "total": 10, "unread_total": 2, "emails": [
            {"id": "1", "from": "A <a@x.com>", "subject": "Привет", "date": "Sun, 2 Aug 2026",
             "unread": True, "snippet": "текст"}, ]},
        ("google", "gmail_list", "5", "--unread"): {"status": "ok", "total": 10, "unread_total": 2, "emails": [
            {"id": "2", "from": "B <b@x.com>", "subject": "Срочно", "date": "Sat, 1 Aug 2026",
             "unread": True, "snippet": "важное"}, ]},
        ("google", "screenshot", "calendar"): {"status": "ok", "title": "Calendar",
                                               "url": "https://calendar.google.com",
                                               "screenshot": "/tmp/aios_acct_google_calendar_test.png"},
        ("instagram", "profile"): {"status": "ok",
                                   "profile": {"username": "jo.talbot", "full_name": "Jo Talbot",
                                               "followers": 54, "following": 159, "posts_count": 0,
                                               "bio": None, "profile_url": "https://instagram.com/jo.talbot/"},
                                   "screenshot": "/tmp/aios_acct_ig_test.png"},
        ("instagram", "posts", "5"): {"status": "ok", "username": "jo.talbot", "posts": []},
        ("instagram", "screenshot"): {"status": "ok", "username": "jo.talbot",
                                      "screenshot": "/tmp/aios_acct_ig_test.png"},
    }


@pytest.fixture(autouse=True)
def _fake(monkeypatch):
    canned = _make_canned()

    def fake_run(args):
        return canned.get(tuple(args), {"status": "error", "error": f"no canned {args}"})

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    m._pending_gmail_send.clear()
    for p in ("/tmp/aios_acct_google_calendar_test.png", "/tmp/aios_acct_ig_test.png"):
        Path(p).write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    yield


def test_email_list_intent():
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "проверь мою почту") is True
    assert any("Последние письма" in x for x in api.messages)


def test_unread_intent():
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "сколько непрочитанных") is True
    assert any("Непрочитанные письма" in x for x in api.messages)


def test_whoami_intent():
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "кто я в гугле") is True
    assert any("jo.talbot@gmail.com" in x for x in api.messages)


def test_instagram_profile_intent():
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "покажи мой инстаграм") is True
    assert api.photos, "ожидалось фото профиля"


def test_calendar_intent():
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "покажи календарь") is True
    assert api.photos


def test_unrelated_text_not_handled():
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "расскажи анекдот") is False
    assert api.messages == []


def test_pending_send_confirmation(monkeypatch):
    def fake_run(args):
        if "gmail_send" in args and "--confirm" in args:
            return {"status": "sent", "to": args[3], "subject": "Тема"}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    m._pending_gmail_send[1] = {"to": "a@b.com", "subject": "Тема", "body": "Текст"}
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "да, отправь") is True
    assert 1 not in m._pending_gmail_send
    assert any("Письмо отправлено" in x for x in api.messages)
