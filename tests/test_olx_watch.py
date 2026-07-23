"""Tests for OLX subscriptions, favorites watch, AutoWatch and the ad editor."""

import json
from datetime import datetime, timezone

import pytest

from aios_core.modules.olx import (
    AdCard,
    AdImprover,
    AutoWatch,
    CardParser,
    FavoritesWatch,
    OLXCollector,
    OLXStorage,
    OwnAd,
    OwnAdEditor,
    OwnAdsParser,
    SubscriptionManager,
    WebhookNotifier,
)
from tests.test_olx_agent import FakeADB, SAMPLE_XML
from tests.test_olx_actions import OWN_XML, _competitors

NOW = datetime(2026, 7, 21, 15, 0, 0, tzinfo=timezone.utc)
EMPTY_XML = "<hierarchy rotation='0'/>"


# --- Search URL filters -------------------------------------------------------


def test_search_deep_link_filters():
    base = OLXCollector.search_deep_link("лобове скло")
    assert (
        base
        == "https://www.olx.ua/d/uk/list/q-%D0%BB%D0%BE%D0%B1%D0%BE%D0%B2%D0%B5-%D1%81%D0%BA%D0%BB%D0%BE/"
        or base.startswith("https://www.olx.ua/d/uk/list/q-лобове-скло/")
    )

    filtered = OLXCollector.search_deep_link(
        "лобове скло", min_price=1000, max_price=8000, sort="filter_float_price:asc"
    )
    assert "filter_float_price%3Afrom%5D=1000" in filtered
    assert "filter_float_price%3Ato%5D=8000" in filtered
    assert "search%5Border%5D=filter_float_price%3Aasc" in filtered


# --- Subscriptions --------------------------------------------------------------


def test_subscription_matching_filters():
    sub = {
        "id": 1,
        "name": "скло до 8000",
        "query": "лобове скло",
        "min_price": 1000.0,
        "max_price": 8000.0,
        "city": None,
    }
    ok = AdCard(title="Скло X", price=7000.0, currency="UAH", city="Київ", query="лобове скло")
    too_expensive = AdCard(title="Скло Y", price=9000.0, currency="UAH", query="лобове скло")
    no_price = AdCard(title="Скло Z", price=None, query="лобове скло")
    assert SubscriptionManager.matches(sub, ok) is True
    assert SubscriptionManager.matches(sub, too_expensive) is False
    assert SubscriptionManager.matches(sub, no_price) is False

    city_sub = {
        "id": 2,
        "name": "київ",
        "query": "скло",
        "min_price": None,
        "max_price": None,
        "city": "Київ",
    }
    from_kyiv = AdCard(title="Лобове скло", price=100.0, city="Київ", query="")
    from_lviv = AdCard(title="Лобове скло", price=100.0, city="Львів", query="")
    # Title-token fallback matches "скло" for empty card query
    assert SubscriptionManager.matches(city_sub, from_kyiv) is True
    assert SubscriptionManager.matches(city_sub, from_lviv) is False


def test_subscription_check_new_alerts():
    storage = OLXStorage()
    manager = SubscriptionManager(storage)
    sub_id = manager.add("скло до 8000", "q", max_price=8000.0)
    cards = CardParser().parse(SAMPLE_XML, query="q")

    alerts = manager.check_new(cards)
    assert len(alerts) == 1
    assert alerts[0]["subscription_id"] == sub_id
    # BMW (7000) passes the max_price filter; Audi has no price → filtered out.
    assert alerts[0]["new_count"] == 1
    assert alerts[0]["ads"][0]["price"] == 7000.0

    # Touch timestamp recorded; re-check without new ads → nothing.
    assert storage.subscriptions_list()[0]["last_checked_at"] is not None
    assert manager.check_new([]) == []
    storage.close()


# --- Favorites watch ----------------------------------------------------------


def test_favorites_watch_lists_and_alerts_on_drop():
    storage = OLXStorage()
    cards = CardParser().parse(SAMPLE_XML, query="q")
    storage.save_ads(cards, seen_at="2026-07-20T10:00:00+00:00")
    bmw = next(card for card in cards if card.url)

    watch = FavoritesWatch(storage)
    assert watch.add(bmw.fingerprint) is True
    assert watch.add(bmw.fingerprint) is False  # already favorite
    listed = watch.list()
    assert len(listed) == 1
    assert listed[0]["title"].startswith("BMW X3")

    assert watch.price_alerts() == []  # no price change yet

    cheaper = AdCard.from_dict(bmw.to_dict())
    cheaper.price = 6200.0
    storage.save_ads([cheaper], seen_at="2026-07-21T10:00:00+00:00")
    alerts = watch.price_alerts()
    assert len(alerts) == 1
    assert alerts[0]["type"] == "favorite_price_drop"
    assert alerts[0]["last_price"] == 6200.0

    assert watch.remove(bmw.fingerprint) is True
    assert watch.list() == []
    storage.close()


# --- Own ad editor --------------------------------------------------------------


def test_own_ad_editor_plan_and_guard():
    own = OwnAd(
        title="Скло лобове",
        price=9000.0,
        url="https://www.olx.ua/d/uk/obyavlenie/test-IDown1a.html",
    )
    suggestion = AdImprover().improve(own, _competitors())

    adb = FakeADB(pages=[])
    editor = OwnAdEditor(adb=adb)
    dry = editor.apply(own, suggestion)
    assert dry["status"] == "dry_run"
    assert any("Редагувати" in step for step in dry["steps"])
    assert adb.commands == []

    executed = editor.apply(own, suggestion, confirm=True)
    assert executed["status"] == "executed"
    assert any("am start" in cmd for cmd in adb.commands)


# --- AutoWatch full cycle ------------------------------------------------------


def test_autowatch_full_cycle():
    sent_events = []

    def poster(url, payload):
        sent_events.append(payload["event"])
        return True

    storage = OLXStorage()
    SubscriptionManager(storage).add("скло", "q")

    # Pre-seed: favorite ad with a price drop + an old stagnant own ad.
    cards = CardParser().parse(SAMPLE_XML, query="q")
    storage.save_ads(cards, seen_at="2026-07-19T10:00:00+00:00")
    bmw = next(card for card in cards if card.url)
    cheaper = AdCard.from_dict(bmw.to_dict())
    cheaper.price = 6500.0
    storage.save_ads([cheaper], seen_at="2026-07-20T10:00:00+00:00")
    storage.favorite_add(bmw.fingerprint)

    old_own = OwnAd(
        title="Скло старе",
        price=1000.0,
        currency="UAH",
        views=2,
        url="https://www.olx.ua/d/uk/obyavlenie/old-IDold9z.html",
    )
    storage.upsert_own_ad(old_own, seen_at="2026-07-01T10:00:00+00:00")

    adb = FakeADB(pages=[EMPTY_XML])  # empty feed this run
    collector = OLXCollector(adb=adb)
    watch = AutoWatch(
        storage=storage,
        collector=collector,
        own_provider=lambda: OwnAdsParser().parse(OWN_XML),
        notifier=WebhookNotifier(url="https://hooks.x/y", poster=poster),
    )

    report = watch.run_cycle(queries=["q"], collect=True)

    assert "collection" in report
    assert report["own_snapshot"]["recorded"] == 2
    assert report["favorite_alerts"], "favorite drop must surface"
    assert report["stagnant"], "old own ad must be stagnant"
    titles = [item["title"] for item in report["stagnant"]]
    assert "Скло старе" in titles
    assert report["suggestions"]
    decision = report["repost_decisions"][0]
    assert decision["should_repost"] is True
    assert decision["plan"], "stagnant ad must come with a repost plan"
    assert report["notifications_sent"] >= 2  # favorite drop + stagnant
    assert "olx_favorite_price_drop" in sent_events
    assert "olx_own_ad_stagnant" in sent_events
    storage.close()


def test_autowatch_without_collect():
    storage = OLXStorage()
    watch = AutoWatch(storage=storage)
    report = watch.run_cycle(collect=False)
    assert report["subscription_alerts"] == []
    assert report["stagnant"] == []
    assert report["notifications_sent"] == 0
    storage.close()


def test_cli_subscribe_favorites_flow(tmp_path, capsys):
    from aios_cli import main

    db = tmp_path / "cli.sqlite"
    storage = OLXStorage(db)
    storage.save_ads(CardParser().parse(SAMPLE_XML, query="q"))
    storage.close()

    main(["olx", "subscribe", "--db", str(db), "--query", "q", "--max-price", "8000"])
    assert json.loads(capsys.readouterr().out)["id"] >= 1

    main(["olx", "subscriptions", "--db", str(db)])
    subs = json.loads(capsys.readouterr().out)
    assert len(subs) == 1 and subs[0]["max_price"] == 8000.0

    main(["olx", "favorites", "--db", str(db)])
    assert json.loads(capsys.readouterr().out) == []

    main(["olx", "autowatch", "--db", str(db), "--no-collect"])
    report = json.loads(capsys.readouterr().out)
    assert report["notifications_sent"] == 0
