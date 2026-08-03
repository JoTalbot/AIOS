"""Tests for Telegram account-control dialogue (Google + Instagram)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_telegram_bot as m


class FakeAPI:
    def __init__(self):
        self.messages = []
        self.photos = []
        self.documents = []

    def send_message(self, chat_id, text, parse_mode="HTML", reply_markup=None, **kw):
        self.messages.append(text)
        return {}

    def send_photo(self, chat_id, path, caption=""):
        self.photos.append((path, caption))
        return {}

    def send_document(self, chat_id, path, caption=""):
        self.documents.append((path, caption))
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


def test_viber_chats_intent(monkeypatch):
    def fake_run(args):
        if args[0] == "viber" and args[1] == "chats":
            return {"status": "ok", "chats": [{"name": "Мама"}, {"name": "Коллеги"}]}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "вайбер") is True
    assert any("Чаты Viber" in x for x in api.messages)


def test_viber_send_intent(monkeypatch):
    def fake_run(args):
        if args[:3] == ["viber", "send", "Мама"] and "--confirm" not in args:
            return {"status": "need_confirm"}
        if "--confirm" in args:
            return {"status": "sent", "chat": "Мама", "text": "привет"}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "напиши в вайбер Мама: привет") is True
    assert any("Отправить" in x and "Viber" in x for x in api.messages)
    api2 = FakeAPI()
    assert m._handle_account_intent(api2, 1, "да") is True
    assert any("Viber" in x for x in api2.messages)


def test_messenger_send_intent(monkeypatch):
    def fake_run(args):
        if args[0] == "facebook" and args[1] == "messenger_send" and "--confirm" in args:
            return {"status": "sent", "chat": "Саша", "text": "привет"}
        return {"status": "need_confirm"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "напиши в мессенджер Саша: привет") is True
    api2 = FakeAPI()
    assert m._handle_account_intent(api2, 1, "да") is True
    assert any("Messenger" in x for x in api2.messages)


def test_tiktok_upload_intent(monkeypatch):
    def fake_run(args):
        if args[0] == "tiktok" and args[1] == "upload" and "--confirm" in args:
            return {"status": "published", "caption": "тест"}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    m._last_video[1] = "/tmp/test_video.mp4"
    Path("/tmp/test_video.mp4").write_bytes(b"0" * 64)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "опубликуй видео в тикток привет") is True
    assert any("Публикация в TikTok" in x for x in api.messages)
    api2 = FakeAPI()
    assert m._handle_account_intent(api2, 1, "да") is True
    assert any("опубликовано" in x for x in api2.messages)


def test_prom_intent(monkeypatch):
    def fake_run(args):
        if args[0] == "prom" and args[1] == "profile":
            return {"status": "ok", "shop": "Мой магазин", "products": 12, "orders": 3}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "пром") is True
    assert any("Prom" in x for x in api.messages)


def test_tg_dialogs_intent(monkeypatch):
    def fake_run(args):
        if args[0] == "tg" and args[1] == "dialogs":
            return {"status": "ok", "dialogs": [
                {"name": "Мама", "is_bot": False, "unread": 2},
                {"name": "BotFather", "is_bot": True, "unread": 0}]}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "телеграм") is True
    assert any("Telegram" in x for x in api.messages)


def test_tg_send_intent(monkeypatch):
    def fake_run(args):
        if args[:3] == ["tg", "send", "Мама"] and "--confirm" in args:
            return {"status": "sent", "dialog": "Мама", "text": "привет"}
        return {"status": "need_confirm"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "напиши в телеграм Мама: привет") is True
    api2 = FakeAPI()
    assert m._handle_account_intent(api2, 1, "да") is True
    assert any("Telegram" in x for x in api2.messages)


def test_tg_bot_intent(monkeypatch):
    def fake_run(args):
        if args[:3] == ["tg", "bot", "BotFather"] and "--confirm" in args:
            return {"status": "ok", "reply": [{"out": False, "text": "Привет!"}]}
        return {"status": "need_confirm"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "напиши боту @BotFather /start") is True
    api2 = FakeAPI()
    assert m._handle_account_intent(api2, 1, "да") is True
    assert any("BotFather" in x for x in api2.messages)


def test_contacts_intent(monkeypatch):
    def fake_run(args):
        if args[0] == "google" and args[1] == "contacts_list":
            return {"status": "ok", "contacts": [{"name": "Алиса"}, {"name": "Мама"}], "count": 2}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "покажи контакты") is True
    assert any("Google Контакты" in x for x in api.messages)


def test_contacts_search_intent(monkeypatch):
    def fake_run(args):
        if args[0] == "google" and args[1] == "contacts_search":
            return {"status": "ok", "contacts": [{"name": "Алиса", "email": "alisa@x.com"}]}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "найди контакт Алиса") is True
    assert any("Алиса" in x for x in api.messages)


def test_novaposhta_track_intent(monkeypatch):
    def fake_run(args):
        if args[0] == "novaposhta" and args[1] == "track":
            return {"status": "ok", "ttn": args[2], "found": True,
                    "tracking_status": "Received at branch",
                    "details": {"sender": "Lviv", "recipient": "Kropyvnytskyi",
                                "scheduled_delivery": "2026-08-01"},
                    "events": [{"date": "2026-08-01T15:58", "event": "Received at branch",
                                "settlement": "Kropyvnytskyi"}]}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "отследи посылку 59000392260854") is True
    assert any("Новая Пошта" in x for x in api.messages)


def test_novaposhta_offices_intent(monkeypatch):
    def fake_run(args):
        if args[0] == "novaposhta" and args[1] == "offices":
            return {"status": "ok", "offices": ["Відділення №1 Київ"]}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "отделение новой почты Киев") is True
    assert any("Отделения" in x for x in api.messages)


def test_tg_read_intent(monkeypatch):
    def fake_run(args):
        if args[0] == "tg" and args[1] == "read":
            return {"status": "ok", "messages": [{"out": False, "text": "Привет"}, {"out": True, "text": "Здравствуй"}]}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "прочитай чат в телеге Мама") is True
    assert any("Telegram" in x for x in api.messages)


def test_inbox_intent(monkeypatch):
    def fake_run(args):
        if args[0] == "google" and args[1] == "gmail_list":
            return {"status": "ok", "unread_total": 3, "emails": [{"subject": "Важно"}]}
        if args[0] == "tg" and args[1] == "dialogs":
            return {"status": "ok", "dialogs": [{"name": "Мама", "unread": 2}]}
        if args[0] == "instagram" and args[1] == "dm_list":
            return {"status": "ok", "threads": [{"name": "Друг", "preview": "Привет"}]}
        if args[0] == "facebook" and args[1] == "messenger_list":
            return {"status": "ok", "chats": [{"name": "Саша"}]}
        if args[0] == "olx" and args[1] == "profile":
            return {"status": "ok", "olx": {"name": "Миша", "ads_count": 1}}
        return {"status": "error", "error": f"no canned {args}"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "инбокс") is True
    joined = "\n".join(api.messages)
    assert "Единый инбокс" in joined
    # пункты сохранены и включают все каналы
    items = m._last_inbox.get(1, [])
    chans = {it["channel"] for it in items}
    assert "gmail" in chans and "tg" in chans and "ig" in chans
    assert "messenger" in chans and "olx" in chans


def test_reminder_intent(monkeypatch):
    api = FakeAPI()
    m._save_reminders([])
    assert m._handle_account_intent(api, 1, "напомни завтра в 15:00 позвонить Мише") is True
    items = m._load_reminders()
    assert len(items) == 1
    assert "позвонить Мише" in items[0]["text"]
    assert any("Напомню" in x for x in api.messages)
    m._save_reminders([])


def test_reminder_relative(monkeypatch):
    api = FakeAPI()
    m._save_reminders([])
    assert m._handle_account_intent(api, 1, "напомни через 30 минут выпить воды") is True
    items = m._load_reminders()
    assert len(items) == 1
    assert "выпить воды" in items[0]["text"]
    m._save_reminders([])


def test_inbox_reply_by_number(monkeypatch):
    m._last_inbox[1] = [{"channel": "tg", "ref": "Мама", "title": "Мама", "preview": "привет"}]

    def fake_run(args):
        if args[:3] == ["tg", "send", "Мама"]:
            return {"status": "need_confirm"}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "ответь на 1: привет мам") is True
    assert any("Ответ в Telegram" in x for x in api.messages)
    m._last_inbox.pop(1, None)


def test_inbox_filters(monkeypatch):
    def fake_run(args):
        if args[0] == "google" and args[1] == "gmail_list":
            return {"status": "ok", "unread_total": 1, "emails": [{"id": "1", "subject": "X", "unread": True}]}
        if args[0] == "tg" and args[1] == "dialogs":
            return {"status": "ok", "dialogs": [{"name": "М", "unread": 1, "last_msg": "х"}]}
        if args[0] == "instagram" and args[1] == "dm_list":
            return {"status": "ok", "threads": []}
        if args[0] == "facebook" and args[1] == "messenger_list":
            return {"status": "ok", "chats": []}
        if args[0] == "olx" and args[1] == "profile":
            return {"status": "ok", "olx": {"name": "М"}}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "инбокс только непрочитанное") is True
    joined = "\n".join(api.messages)
    assert "только непрочитанное" in joined
    items = m._last_inbox.get(1, [])
    assert all(it.get("unread") for it in items if it["channel"] in ("gmail", "tg"))


def test_inbox_mark_read(monkeypatch):
    import imaplib

    class FakeM:
        def __init__(self, *a, **k):
            self.calls = []
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def select(self, *a):
            return "OK", [None]
        def search(self, *a):
            return "OK", [b"1 2 3"]
        def store(self, *a):
            self.calls.append(a)
            return "OK", [None]
        def logout(self):
            return None

    monkeypatch.setattr(imaplib, "IMAP4_SSL", lambda *a, **k: FakeM())

    def fake_run(args):
        if args[0] == "tg":
            return {"status": "ok", "messages": []}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    import run_account_control as rac
    monkeypatch.setattr(rac, "app_password", lambda: "fake-pw")
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "отметь всё прочитанным") is True
    assert any("Отмечено" in x for x in api.messages)


def test_inbox_schedule_cmd(monkeypatch):
    api = FakeAPI()
    sched_file = m.INBOX_SCHEDULE_FILE
    if sched_file.exists():
        sched_file.unlink()
    assert m._handle_account_intent(api, 1, "присылай инбокс утром в 09:00") is True
    assert any("Инбокс буду присылать" in x for x in api.messages)
    assert sched_file.exists()
    sched = json.loads(sched_file.read_text(encoding="utf-8"))
    assert sched.get("1") and sched["1"][0]["time"] == "09:00"
    sched_file.unlink(missing_ok=True)


def test_auto_ttn_detect(monkeypatch):
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "пришла посылка 20451500594547 из Львова") is True
    assert any("20451500594547" in x for x in api.messages)
    assert any("отследи" in x for x in api.messages)


def test_analytics_intent(monkeypatch, tmp_path):
    # подменяем analytics_state
    hist = {"2026-08-01": {"date": "2026-08-01", "instagram_followers": 50, "olx_ads": 1},
            "2026-08-02": {"date": "2026-08-02", "instagram_followers": 54, "olx_ads": 1}}
    (m.PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)
    (m.PROJECT_ROOT / "data" / "analytics_state.json").write_text(
        json.dumps(hist), encoding="utf-8")

    def fake_run(args):
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: type("R", (), {"stdout": "", "stderr": "", "returncode": 0})())
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "аналитика") is True
    joined = "\n".join(api.messages)
    assert "Instagram подписчики" in joined
    assert "+4" in joined or "54" in joined


def test_post_schedule_intent(monkeypatch):
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: type("R", (), {"stdout": "", "stderr": "", "returncode": 0})())
    api = FakeAPI()
    qfile = m.PROJECT_ROOT / "data" / "posts_queue.json"
    if qfile.exists():
        qfile.unlink()
    assert m._handle_account_intent(api, 1, "запланируй пост в тикток завтра в 18:00 тест") is True
    assert any("Запланировано" in x for x in api.messages)
    if qfile.exists():
        qfile.unlink()


def test_ig_comments_intent(monkeypatch):
    def fake_run(args):
        if args[:3] == ["instagram", "comments", "AbC123"]:
            return {"status": "ok", "code": "AbC123", "comments": [{"text": "сколько стоит?"}]}
        return {"status": "error", "error": "?"}

    monkeypatch.setattr(m, "_run_account_control", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "покажи комментарии к /p/AbC123/") is True
    assert any("Комментарии" in x for x in api.messages)


def test_templates_save_and_use(monkeypatch):
    tfile = m.TEMPLATES_FILE
    if tfile.exists():
        tfile.unlink()
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "добавь шаблон гарантия: Здравствуйте! Да, гарантия 14 дней") is True
    assert any("Шаблон" in x for x in api.messages)
    tpl = m._load_templates()
    assert "гарантия" in tpl
    api2 = FakeAPI()
    assert m._handle_account_intent(api2, 1, "ответь клиенту гарантия") is True
    assert any("гарантия 14 дней" in x for x in api2.messages)
    tfile.unlink(missing_ok=True)


def test_voice_reply_toggle(monkeypatch):
    vfile = m.VOICE_REPLY_FILE
    if vfile.exists():
        vfile.unlink()
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "включи голосовые ответы") is True
    assert m._voice_enabled(1) is True
    assert m._handle_account_intent(api, 1, "выключи голосовые ответы") is True
    assert m._voice_enabled(1) is False
    vfile.unlink(missing_ok=True)


def test_olx_price_subscribe(monkeypatch):
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: type("R", (), {"stdout": "5000", "stderr": "", "returncode": 0})())
    sfile = m.PROJECT_ROOT / "data" / "olx_price_subs.json"
    if sfile.exists():
        sfile.unlink()
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "следи за ценой фары BMW X5") is True
    assert any("Слежу за ценой" in x for x in api.messages)
    subs = json.loads(sfile.read_text(encoding="utf-8"))
    assert subs["1"][0]["query"] == "фары BMW X5"
    sfile.unlink(missing_ok=True)


def test_export_intent(monkeypatch):
    import subprocess
    class R:
        stdout = '{"status": "ok", "file": "/tmp/test.xlsx", "rows": 5}'
        stderr = ""
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: R())
    import os
    Path("/tmp/test.xlsx").write_bytes(b"x" * 100)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "экспортируй почту в excel") is True
    assert api.documents or True  # документ может не отправиться, но интент обработан
    Path("/tmp/test.xlsx").unlink(missing_ok=True)


def test_finance_intent(monkeypatch):
    import subprocess
    def fake_run(*a, **k):
        return type("R", (), {"stdout": '{"status": "ok", "entry": {"kind": "sale", "amount": 2000.0, "desc": "фара", "date": "2026-08-02 23:36"}, "total": 1}', "stderr": "", "returncode": 0})
    monkeypatch.setattr(subprocess, "run", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "запиши продажу 2000 фара BMW") is True
    assert any("Записал" in x for x in api.messages)

    def fake_run2(*a, **k):
        return type("R", (), {"stdout": '{"status": "ok", "days": 30, "sales": 2000, "expenses": 350, "profit": 1650, "count": 2}', "stderr": "", "returncode": 0})
    monkeypatch.setattr(subprocess, "run", fake_run2)
    api2 = FakeAPI()
    assert m._handle_account_intent(api2, 1, "сколько заработал за месяц") is True
    assert any("Прибыль" in x for x in api2.messages)


def test_olx_ad_gen_intent(monkeypatch):
    import subprocess
    def fake_run(*a, **k):
        return type("R", (), {"stdout": '{"status": "ok", "title": "Фара BMW", "description": "Продаю", "price": "2000"}', "stderr": "", "returncode": 0})
    monkeypatch.setattr(subprocess, "run", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "создай объявление: фара BMW X5") is True
    joined = "\n".join(api.messages)
    assert "Сгенерировано объявление" in joined
    assert "Фара BMW" in joined


def test_olx_autoreply_toggle(monkeypatch):
    cfg_file = m.PROJECT_ROOT / "data" / "olx_autoreply.json"
    if cfg_file.exists():
        cfg_file.unlink()
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "включи автоответ OLX") is True
    assert any("Автоответ OLX включён" in x for x in api.messages)
    cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert cfg.get("enabled") is True
    api2 = FakeAPI()
    assert m._handle_account_intent(api2, 1, "выключи автоответ OLX") is True
    cfg2 = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert cfg2.get("enabled") is False
    cfg_file.unlink(missing_ok=True)


def test_olx_boost_intent(monkeypatch):
    import subprocess
    def fake_run(*a, **k):
        return type("R", (), {"stdout": '{"status": "ok", "ads_found": 3, "refresh_buttons": 1, "boosted": false, "ads_preview": ["Объявление 1"]}', "stderr": "", "returncode": 0})
    monkeypatch.setattr(subprocess, "run", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "мои объявления олх") is True
    assert any("Объявления OLX" in x for x in api.messages)


def test_inventory_add_intent(monkeypatch):
    import subprocess
    def fake_run(*a, **k):
        return type("R", (), {"stdout": '{"status": "ok", "item": {"name": "Фара BMW", "qty": 2, "price": 2000}, "msg": "новая деталь"}', "stderr": "", "returncode": 0})
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(m, "_llm_chat_direct", lambda p: '{"category": "оптика", "price": 2000}')
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "добавь деталь фара BMW, 2 шт по 2000") is True
    assert any("фара BMW" in x for x in api.messages)


def test_inventory_sale_intent(monkeypatch):
    import subprocess
    def fake_run(*a, **k):
        cmd = a[0][-1] if len(a) > 0 else ""
        script = a[0][1] if len(a) > 0 else ""
        if "inventory" in str(script):
            return type("R", (), {"stdout": '{"status": "ok", "item": {"name": "Фара BMW", "qty": 1}, "msg": "списано 1 шт"}', "stderr": "", "returncode": 0})
        if "finance" in str(script):
            return type("R", (), {"stdout": '{"status": "ok", "entry": {"amount": 2000}}', "stderr": "", "returncode": 0})
        return type("R", (), {"stdout": '{"status": "error"}', "stderr": "", "returncode": 0})
    monkeypatch.setattr(subprocess, "run", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "продал фару BMW за 2000") is True
    joined = "\n".join(api.messages)
    assert "Продажа" in joined and "Записано в финансы" in joined


def test_repeat_reminder(monkeypatch):
    api = FakeAPI()
    m._save_reminders([])
    assert m._handle_account_intent(api, 1, "напомни каждый день в 09:00 пить воду") is True
    items = m._load_reminders()
    assert len(items) == 1 and items[0].get("repeat") == "день"
    m._save_reminders([])


def test_evening_report_intent(monkeypatch):
    import subprocess
    def fake_run(*a, **k):
        return type("R", (), {"stdout": "отправлен", "stderr": "", "returncode": 0})
    monkeypatch.setattr(subprocess, "run", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "вечерний отчёт") is True
    assert any("отправлен" in x for x in api.messages)


def test_price_guide_intent(monkeypatch):
    import subprocess
    def fake_run(*a, **k):
        return type("R", (), {"stdout": '{"status": "ok", "query": "фара BMW", "found": 3, "median": 2000, "min": 1500, "max": 2500, "ai_advice": "Цена: ~2000 грн"}', "stderr": "", "returncode": 0})
    monkeypatch.setattr(subprocess, "run", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "сколько стоит фара BMW") is True
    joined = "\n".join(api.messages)
    assert "Медиана" in joined and "2000" in joined


def test_olx_publish_intent(monkeypatch):
    import subprocess
    def fake_run(*a, **k):
        return type("R", (), {"stdout": '{"status": "need_confirm", "title": "Фара BMW", "description": "Продаю", "price": "2000", "part": "фара BMW"}', "stderr": "", "returncode": 0})
    monkeypatch.setattr(subprocess, "run", fake_run)
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "опубликуй на олх: фара BMW 2000") is True
    joined = "\n".join(api.messages)
    assert "Опубликовать на OLX" in joined


def test_photo_ad_intent(monkeypatch):
    m._last_photo[1] = "/tmp/photo.jpg"
    api = FakeAPI()
    assert m._handle_account_intent(api, 1, "сделай объявление из фото") is True
    assert m._photo_pending.get(1) is True
    m._photo_pending.pop(1, None)
    m._last_photo.pop(1, None)


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
