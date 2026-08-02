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
        ("google", "gmail_search", "github", "5"): {"status": "ok", "total": 3, "emails": [
            {"id": "9", "from": "GitHub <noreply@github.com>", "subject": "Re: PR",
             "date": "Fri, 31 Jul 2026", "unread": False, "snippet": "комментарий"}, ]},
        ("google", "screenshot", "calendar"): {"status": "ok", "title": "Calendar",
                                               "url": "https://calendar.google.com",
                                               "screenshot": "/tmp/aios_acct_google_calendar_test.png"},
        ("google", "calendar_events"): {"status": "ok", "title": "Calendar",
                                        "events": ["Встреча 14:00", "Созвон 16:00"],
                                        "screenshot": "/tmp/aios_acct_cal_events_test.png"},
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
    m._pending_confirm.clear()
    m._last_photo.clear()
    for p in ("/tmp/aios_acct_google_calendar_test.png", "/tmp/aios_acct_ig_test.png",
              "/tmp/aios_acct_cal_events_test.png"):
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


def test_calendar_screenshot_intent():
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "покажи календарь") is True
    assert api.photos


def test_calendar_events_intent():
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "события на сегодня") is True
    assert any("События на сегодня" in x for x in api.messages)
    assert api.photos, "ожидался скрин календаря"


def test_gmail_search_intent():
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "найди письмо от github") is True
    assert any("Re: PR" in x for x in api.messages)


def test_story_intent_not_supported():
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "опубликуй сторис") is True
    assert any("Сторис" in x for x in api.messages)


def test_unrelated_text_not_handled():
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "расскажи анекдот") is False
    assert api.messages == []


def test_pending_gmail_send_confirmation(monkeypatch):
    def fake_run(args):
        if "gmail_send" in args and "--confirm" in args:
            return {"status": "sent", "to": args[3], "subject": "Тема"}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    m._pending_confirm[1] = {"kind": "gmail",
                             "data": {"to": "a@b.com", "subject": "Тема", "body": "Текст"}}
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "да, отправь") is True
    assert 1 not in m._pending_confirm
    assert any("Письмо отправлено" in x for x in api.messages)


def test_calendar_add_flow(monkeypatch):
    canned_cal = {"status": "need_confirm", "title": "Встреча", "start": "2026-08-03T14:00:00",
                  "end": "2026-08-03T15:00:00", "screenshot": "/tmp/aios_acct_cal_add_test.png"}
    Path("/tmp/aios_acct_cal_add_test.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)

    def fake_run(args):
        if args[0] == "google" and args[1] == "calendar_add" and "--confirm" not in args:
            return canned_cal
        if args[0] == "google" and args[1] == "calendar_add" and "--confirm" in args:
            return {"status": "ok", "title": "Встреча", "start": "2026-08-03T14:00:00",
                    "end": "2026-08-03T15:00:00", "url": "https://calendar.google.com/"}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    monkeypatch.setattr(m, "_llm_extract_calendar",
                        lambda t: {"title": "Встреча", "date": "2026-08-03", "time": "14:00", "desc": ""})
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "добавь событие Встреча завтра в 14:00") is True
    assert any("Подтвердите создание" in x for x in api.messages)
    # подтверждаем
    api2 = FakeAPI()
    assert m._handle_account_intent(api2, 1, "да") is True
    assert any("Событие создано" in x for x in api2.messages)


def test_facebook_intent(monkeypatch):
    def fake_run(args):
        if args[0] == "facebook" and args[1] == "profile":
            return {"status": "ok", "facebook": {"name": "qililip",
                                                 "profile_url": "https://www.facebook.com/qililip",
                                                 "notifications": 2}}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "покажи фейсбук") is True
    assert any("Facebook" in x for x in api.messages)


def test_tiktok_intent(monkeypatch):
    def fake_run(args):
        if args[0] == "tiktok" and args[1] == "profile":
            return {"status": "ok", "tiktok": {"username": "jotalbotkubik",
                                               "name": "Jo Talbot565", "followers": 2,
                                               "following": 1, "likes": 0}}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "тикток") is True
    assert any("TikTok" in x for x in api.messages)


def test_olx_intent(monkeypatch):
    def fake_run(args):
        if args[0] == "olx" and args[1] == "profile":
            return {"status": "ok", "olx": {"name": "Миша", "ads_count": 1, "balance": "0"}}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "покажи олх") is True
    assert any("OLX" in x for x in api.messages)


def test_ig_like_flow(monkeypatch):
    def fake_run(args):
        if args[:3] == ["instagram", "like", url] and "--confirm" not in args:
            return {"status": "need_confirm", "action": "like", "url": url}
        if "--confirm" in args:
            return {"status": "liked", "url": url}
        return {"status": "error", "error": "?"}

    url = "https://www.instagram.com/p/AbC123/"
    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, f"лайкни {url}") is True
    assert any("Поставить лайк" in x for x in api.messages)
    api2 = FakeAPI()
    assert m._handle_account_intent(api2, 1, "да") is True
    assert any("Лайк поставлен" in x for x in api2.messages)


def test_ig_follow_flow(monkeypatch):
    def fake_run(args):
        if args[:3] == ["instagram", "follow", "dawnrichard"] and "--confirm" not in args:
            return {"status": "need_confirm", "action": "follow", "username": "dawnrichard"}
        if "--confirm" in args:
            return {"status": "ok", "action": "follow", "username": "dawnrichard"}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "подпишись на @dawnrichard") is True
    assert any("подписаться на @dawnrichard" in x for x in api.messages)
    api2 = FakeAPI()
    assert m._handle_account_intent(api2, 1, "да") is True
    assert any("подписался на @dawnrichard" in x for x in api2.messages)


def test_docs_intent(monkeypatch):
    def fake_run(args):
        if args[0] == "google" and args[1] == "docs_create":
            return {"status": "ok", "url": "https://docs.google.com/document/d/x/"}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    monkeypatch.setattr(m, "_llm_extract_gmail",
                        lambda t: {"subject": "Тест", "body": "Текст документа"})
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "создай документ") is True
    assert any("Документ создан" in x for x in api.messages)


def test_dm_list_intent(monkeypatch):
    def fake_run(args):
        if args[:3] == ["instagram", "dm_list", "10"]:
            return {"status": "ok", "threads": [
                {"name": "Серега Потуроев", "preview": "Привет", "time": "1 год"}]}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "директ") is True
    assert any("Чаты Direct" in x for x in api.messages)


def test_dm_read_intent(monkeypatch):
    def fake_run(args):
        if args[0] == "instagram" and args[1] == "dm_read":
            return {"status": "ok", "messages": [{"text": "привет"}, {"text": "как дела"}]}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "покажи чат Серега") is True
    assert any("Последние сообщения" in x for x in api.messages)


def test_dm_send_intent(monkeypatch):
    def fake_run(args):
        if args[:3] == ["instagram", "dm_send", "Серега"] and "--confirm" not in args:
            return {"status": "need_confirm"}
        if "--confirm" in args:
            return {"status": "sent", "thread": "Серега", "text": "привет"}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "напиши в директ Серега: привет") is True
    assert any("Подтвердите" in x for x in api.messages)
    api2 = FakeAPI()
    assert m._handle_account_intent(api2, 1, "да") is True
    assert any("Отправлено" in x for x in api2.messages)
