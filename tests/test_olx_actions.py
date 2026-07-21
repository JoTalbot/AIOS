"""Tests for OLX detail parsing, messaging, own-ads tracking, promotion,
repost planning, notifications and MCP tool integration."""

import json
from datetime import datetime, timezone

import pytest

from aios_core.modules.olx import (
    AdCard,
    AdDetailParser,
    AdImprover,
    ChatListParser,
    ChatViewParser,
    Message,
    OLXMessenger,
    OLXStorage,
    OwnAd,
    OwnAdsParser,
    OwnAdsTracker,
    PriceTracker,
    ReplySuggester,
    RepostPlanner,
    Reposter,
    WebhookNotifier,
    notify_price_drops,
    notify_stagnant,
)
from tests.test_olx_agent import FakeADB, SAMPLE_XML
from aios_core.modules.olx import CardParser

NOW = datetime(2026, 7, 21, 15, 0, 0, tzinfo=timezone.utc)

DETAIL_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="Лобове скло BMW X3 G01 оригінал" resource-id="ua.slando:id/adTitle"
        bounds="[24,80][1056,140]"/>
  <node text="7 000 грн" bounds="[24,160][400,210]"/>
  <node text="Опубліковано 12 липня 2026" bounds="[24,220][600,260]"/>
  <node text="Стан: Б/у" bounds="[24,300][400,340]"/>
  <node text="Доставка OLX: Так" bounds="[24,350][500,390]"/>
  <node text="Скло у відмінному стані, зняте з авто BMW X3 G01 2019 року. Без тріщин та сколів, повний комплект кріплень."
        resource-id="ua.slando:id/adDescription" bounds="[24,420][1056,700]"/>
  <node text="Дніпро" bounds="[24,730][300,770]"/>
  <node text="Переглядів: 342" bounds="[24,780][400,820]"/>
  <node text="Приватна особа" bounds="[24,900][400,940]"/>
  <node text="Олена" bounds="[24,950][300,990]"/>
  <node text="На OLX з квіт. 2021" bounds="[24,1000][500,1040]"/>
</hierarchy>
"""

CHATS_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node resource-id="ua.slando:id/chatItemRoot" bounds="[0,100][1080,300]">
    <node text="Олексій"/><node text="Лобове скло BMW X3"/>
    <node text="Добрий день! Ще актуально?"/><node text="12:30"/>
    <node text="2" resource-id="ua.slando:id/unreadBadge"/>
  </node>
  <node resource-id="ua.slando:id/chatItemRoot" bounds="[0,300][1080,500]">
    <node text="Марічка"/><node text="Скло заднє Audi A4"/>
    <node text="Чекаю на відповідь"/><node text="Вчора"/>
  </node>
</hierarchy>
"""

CHAT_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="Добрий день" bounds="[10,100][700,140]"/>
  <node text="Ще актуально?" bounds="[10,160][700,200]"/>
  <node text="12:38" bounds="[420,240][660,270]"/>
  <node text="Так, актуально" bounds="[400,280][1070,320]"/>
  <node text="А віддасте за 6000?" bounds="[10,360][700,400]"/>
</hierarchy>
"""

OWN_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node resource-id="ua.slando:id/myAdCard" bounds="[0,100][1080,500]">
    <node text="Лобове скло BMW X3 G01"/>
    <node text="6 700 грн"/>
    <node text="Переглядів: 35"/>
    <node text="В обраних: 2"/>
    <node text="Повідомлень: 1"/>
    <node content-desc="https://www.olx.ua/d/uk/obyavlenie/test-IDown1a.html"/>
  </node>
  <node resource-id="ua.slando:id/myAdCard" bounds="[0,500][1080,900]">
    <node text="Скло заднє Audi A4"/>
    <node text="2 500 грн"/>
    <node text="Переглядів: 3"/>
    <node text="Неактивне"/>
  </node>
</hierarchy>
"""


# --- Detail page parser ------------------------------------------------------


def test_detail_parser_extracts_full_page():
    detail = AdDetailParser().parse(DETAIL_XML)

    assert detail.title == "Лобове скло BMW X3 G01 оригінал"
    assert detail.price == 7000.0
    assert detail.currency == "UAH"
    assert "2019" in detail.description
    assert detail.params.get("Стан") == "Б/у"
    assert detail.views_count == 342
    assert detail.seller_type == "private"
    assert detail.seller_name == "Олена"
    assert detail.seller_since == "квіт. 2021"
    assert detail.published_at is not None
    assert detail.city == "Дніпро"
    assert detail.to_dict()["seller_name"] == "Олена"


# --- Chats parsing ------------------------------------------------------------


def test_chat_list_parser_extracts_threads():
    threads = ChatListParser().parse(CHATS_XML)
    assert len(threads) == 2

    first = threads[0]
    assert first.interlocutor == "Олексій"
    assert first.ad_title == "Лобове скло BMW X3"
    assert first.snippet == "Добрий день! Ще актуально?"
    assert first.unread_count == 2
    assert first.updated_text == "12:30"
    assert first.tap_center == (540, 200)
    assert first.key == threads[0].key  # stable

    second = threads[1]
    assert second.unread_count == 0
    assert second.updated_text == "Вчора"


def test_chat_view_parser_direction_detection():
    messages = ChatViewParser(screen_width=1080).parse(CHAT_XML)

    assert [m.author for m in messages] == ["them", "them", "me", "them"]
    assert messages[1].text == "Ще актуально?"
    assert messages[2].ts_text == "12:38"  # time node binds to next bubble
    assert messages[-1].text == "А віддасте за 6000?"


# --- Reply suggestion ---------------------------------------------------------


def test_reply_suggester_availability_intent():
    msgs = [Message(author="them", text="Добрий день! Ще актуально?")]
    reply = ReplySuggester().suggest(msgs, my_price=7000.0, title="скло BMW X3")
    assert "актуальн" in reply
    assert "скло BMW X3" in reply


def test_reply_suggester_bargain_accept_and_counter():
    suggester = ReplySuggester(min_price_ratio=0.85)

    accept = suggester.suggest(
        [Message(author="them", text="Віддасте за 6700?")], my_price=7000.0
    )
    assert "домовились за 6700" in accept

    counter = suggester.suggest(
        [Message(author="them", text="А віддасте за 4000?")], my_price=7000.0
    )
    assert "За 4000 грн, на жаль" in counter
    assert str(int(round(7000 * 0.95))) in counter


def test_reply_suggester_meeting_and_greeting_and_no_reply_needed():
    suggester = ReplySuggester()

    meeting = suggester.suggest(
        [Message(author="them", text="Коли можна подивитись?")], city="Дніпро"
    )
    assert "Дніпро" in meeting

    greeting = suggester.suggest([Message(author="them", text="Добрый день!")])
    assert "Дякую" in greeting

    no_reply = suggester.suggest([Message(author="me", text="Відповів вже")])
    assert no_reply is None


# --- Messenger with guarded outbox --------------------------------------------


def test_messenger_queues_without_auto_send_and_flushes():
    storage = OLXStorage()
    adb = FakeADB(pages=[])
    messenger = OLXMessenger(adb=adb, storage=storage)

    result = messenger.send_reply("chat1", "Добрий день!", interlocutor="Олексій")
    assert result["status"] == "queued"
    assert result["outbox_id"] is not None
    assert len(storage.outbox_pending()) == 1

    flushed = messenger.flush_outbox()
    assert flushed == [{"id": result["outbox_id"], "status": "sent"}]
    assert storage.outbox_pending() == []
    sent = storage.outbox_list(status="sent")
    assert len(sent) == 1
    assert sent[0]["sent_at"] is not None
    assert any("input text" in cmd for cmd in adb.commands)
    assert any("keyevent" in cmd for cmd in adb.commands)
    storage.close()


def test_messenger_marks_failed_when_adb_errors():
    class FailingADB(FakeADB):
        def run(self, command):
            return {"code": 1, "stdout": "", "stderr": "device offline"}

    storage = OLXStorage()
    messenger = OLXMessenger(adb=FailingADB(pages=[]), storage=storage)
    result = messenger.send_reply("chat1", "Привіт", auto_send=True)
    assert result["status"] == "sent"  # attempted
    failed = storage.outbox_list(status="failed")
    assert len(failed) == 1
    assert "device offline" in failed[0]["result"]
    storage.close()


def test_outbox_cancel_transition():
    storage = OLXStorage()
    outbox_id = storage.enqueue_outbox("chat9", "Черновик", interlocutor="Хтось")
    assert storage.outbox_mark(outbox_id, "cancelled") is True
    assert storage.outbox_list(status="pending") == []
    assert storage.outbox_list(status="cancelled")[0]["text"] == "Черновик"
    storage.close()


# --- Own ads parsing & tracking -------------------------------------------------


def test_own_ads_parser_counters_and_status():
    ads = OwnAdsParser().parse(OWN_XML)
    assert len(ads) == 2

    first = ads[0]
    assert first.title == "Лобове скло BMW X3 G01"
    assert first.price == 6700.0
    assert first.views == 35
    assert first.favorites == 2
    assert first.messages == 1
    assert first.status == "active"
    assert first.ad_id == "own1a"  # capture group after the "-ID" marker

    second = ads[1]
    assert second.status == "inactive"
    assert second.views == 3


def test_own_ads_tracker_snapshot_deltas_and_stagnation():
    storage = OLXStorage()
    tracker = OwnAdsTracker(storage)

    ads = OwnAdsParser().parse(OWN_XML)
    first = tracker.record_snapshot(ads, seen_at="2026-07-10T10:00:00+00:00")
    assert first["recorded"] == 2
    assert first["new"] == 2

    # Second snapshot: BMW gains +5 views, +1 favorite.
    grown = OwnAdsParser().parse(OWN_XML.replace("Переглядів: 35", "Переглядів: 40").replace("В обраних: 2", "В обраних: 3"))
    second = tracker.record_snapshot(grown, seen_at="2026-07-11T10:00:00+00:00")
    assert second["new"] == 0
    fp = ads[0].fingerprint
    assert second["deltas"][fp]["views_delta"] == 5
    assert second["deltas"][fp]["favorites_delta"] == 1

    history = storage.own_ad_history(fp)
    assert [point["views"] for point in history] == [35, 40]

    # The ad is 11 days old with 40 views → 3.6/day ≥ 1 — not stagnant
    # with the Audi (3 views, same age) it qualifies... Audi is inactive,
    # only active ads are considered.
    stagnant = tracker.stagnant(min_age_days=3, min_views_per_day=10.0, now=NOW)
    assert len(stagnant) == 1
    assert stagnant[0]["fingerprint"] == fp
    assert "переглядів" in stagnant[0]["reason"]
    storage.close()


# --- Improvement & reposting ----------------------------------------------------


def _competitors():
    return [
        AdCard(title="Лобове скло BMW X3 з підігрівом оригінал", price=6800.0,
               currency="UAH", city="Київ"),
        AdCard(title="Скло лобове BMW X3 оригінал", price=7000.0,
               currency="UAH", city="Дніпро"),
        AdCard(title="Лобове скло Mercedes оригінал", price=7200.0,
               currency="UAH", city="Львів"),
    ]


def test_ad_improver_suggests_title_keywords_and_price():
    own = OwnAd(title="Скло лобове", price=9000.0, currency="UAH")
    suggestion = AdImprover().improve(own, _competitors())

    assert suggestion.suggested_price == round(7000.0 * 0.97)
    assert suggestion.price_verdict == "above_market"
    assert suggestion.keywords_to_add
    if suggestion.suggested_title != own.title:
        assert suggestion.suggested_title.startswith("Скло лобове")
    assert suggestion.description_additions
    assert "ракурс" in suggestion.description_additions[-2]
    assert "медіану" in suggestion.notes[0]


def test_repost_planner_decisions():
    planner = RepostPlanner(min_age_days=3, min_views_per_day=1.0)

    too_young = planner.decide("2026-07-20T15:00:00+00:00", views_total=0, now=NOW)
    assert too_young.should_repost is False

    working = planner.decide(
        "2026-07-10T15:00:00+00:00", views_total=5, messages_total=2, now=NOW
    )
    assert working.should_repost is False

    stale = planner.decide("2026-07-05T15:00:00+00:00", views_total=4, now=NOW)
    assert stale.should_repost is True
    assert stale.best_hours_local == [18, 19, 20, 21]
    assert "переклад" in stale.reason or "перевикласти" in stale.reason


def test_reposter_dry_run_and_confirm():
    own = OwnAd(title="Скло лобове", price=7000.0,
                url="https://www.olx.ua/d/uk/obyavlenie/test-IDown1a.html")

    adb = FakeADB(pages=[])
    dry = Reposter(adb=adb).repost(own)
    assert dry["status"] == "dry_run"
    assert dry["executed"] is False
    assert len(dry["steps"]) >= 5
    assert "дублів" in dry["warning"]
    assert adb.commands == []  # nothing touched the device

    executed = Reposter(adb=adb).repost(own, confirm=True)
    assert executed["status"] == "executed"
    assert any("am start" in cmd for cmd in adb.commands)


# --- Notifications ---------------------------------------------------------------


def test_notifier_webhook_and_telegram_payload():
    captured = []

    def poster(url, payload):
        captured.append((url, payload))
        return True

    storage = OLXStorage()
    cards = CardParser().parse(SAMPLE_XML, query="q")
    storage.save_ads(cards, seen_at="2026-07-20T10:00:00+00:00")
    bmw = next(card for card in cards if card.url)
    cheaper = AdCard.from_dict(bmw.to_dict())
    cheaper.price = 6500.0
    storage.save_ads([cheaper], seen_at="2026-07-21T10:00:00+00:00")

    notifier = WebhookNotifier(url="https://hooks.example.com/x", poster=poster)
    summary = notify_price_drops(PriceTracker(storage), notifier, query="q")
    assert summary == {"alerts": 1, "sent": 1}
    url, payload = captured[0]
    assert payload["event"] == "olx_price_drop"
    assert payload["data"]["last_price"] == 6500.0

    # Telegram-shaped payload
    tg = WebhookNotifier(
        url="https://api.telegram.org/botX/sendMessage", poster=poster, chat_id="42"
    )
    assert tg.send("olx_price_drop", {"title": "t"}) is True
    assert captured[-1][1]["chat_id"] == "42"
    assert "olx_price_drop" in captured[-1][1]["text"]

    sent = notify_stagnant(
        [{"fingerprint": "x", "title": "Скло", "reason": "застій"}],
        WebhookNotifier(url="https://hooks.example.com/x", poster=poster),
    )
    assert sent == {"alerts": 1, "sent": 1}

    # No URL → silent no-op
    assert WebhookNotifier(url=None, poster=poster).send("e", {}) is False
    storage.close()


# --- MCP tools ---------------------------------------------------------------------


def test_mcp_olx_tools_registered_and_callable(tmp_path, monkeypatch):
    import os
    from aios_core.mcp.gateway import MCPGateway, GatewayConfig
    from aios_core.storage import Database

    db_path = tmp_path / "olx.sqlite"
    storage = OLXStorage(db_path)
    storage.save_ads(CardParser().parse(SAMPLE_XML, query="q"))
    storage.close()
    monkeypatch.setenv("AIOS_OLX_DB", str(db_path))

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gateway = MCPGateway(
        config=GatewayConfig(
            constitution_dir=os.path.join(root, "docs/constitution"),
            policies_dir=os.path.join(root, "policies"),
            db_path=":memory:",
        ),
        db=Database(db_path=":memory:"),
    )

    listed = json.loads(gateway.handle_request(json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    )))
    names = [tool["name"] for tool in listed["result"]["tools"]]
    assert "olx_market_stats" in names
    assert "olx_listing_recommend" in names
    assert "olx_price_drops" in names

    response = json.loads(gateway.handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "olx_market_stats", "arguments": {"query": "q"}},
    })))
    assert "error" not in response, response.get("error")
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["total_ads"] == 2
    assert payload["median_price"] == 7000.0
