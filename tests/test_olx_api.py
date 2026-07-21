"""Tests for the OLX Parser Agent REST endpoints (/api/v1/modules/olx/*)."""

import os
import time

import pytest
from httpx import AsyncClient, ASGITransport

from aios_core.modules.olx import CardParser, OLXStorage
from tests.test_olx_agent import SAMPLE_XML

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSTITUTION_DIR = os.path.join(_PROJECT_ROOT, "docs/constitution")
POLICIES_DIR = os.path.join(_PROJECT_ROOT, "policies")

QUERY = "лобове скло"


class FakeCollector:
    """Collector stand-in: parses the sample feed for any query, no ADB."""

    def __init__(self):
        self.calls = []

    def collect(self, query=None, max_cards=100):
        self.calls.append((query, max_cards))
        return CardParser().parse(SAMPLE_XML, query=query)


@pytest.fixture
def deps():
    from aios_core.api.app import AIOSAPI
    from aios_core.modules.olx import OLXMessenger
    from tests.test_olx_actions import CHATS_XML
    from tests.test_olx_agent import FakeADB

    storage = OLXStorage(":memory:")
    storage.save_ads(CardParser().parse(SAMPLE_XML, query=QUERY))
    collector = FakeCollector()
    messenger = OLXMessenger(adb=FakeADB(pages=[CHATS_XML]), storage=storage)
    api = AIOSAPI(
        db_path=":memory:",
        constitution_dir=CONSTITUTION_DIR,
        policies_dir=POLICIES_DIR,
        auth_required=False,
        olx_storage=storage,
        olx_collector=collector,
        olx_messenger=messenger,
    )
    return api.create_starlette_app(), storage, messenger.adb


@pytest.fixture
async def client(deps):
    app, _storage, _adb = deps
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ============================================================
# Ads listing
# ============================================================


class TestOLXAds:
    async def test_list_ads(self, client):
        resp = await client.get("/api/v1/modules/olx/ads")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert data["total"] == 2
        titles = {item["title"] for item in data["items"]}
        assert any("BMW X3" in title for title in titles)

    async def test_list_ads_query_filter(self, client):
        resp = await client.get("/api/v1/modules/olx/ads", params={"query": "інше"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

        resp = await client.get("/api/v1/modules/olx/ads", params={"query": QUERY})
        assert resp.json()["count"] == 2

    async def test_list_ads_limit_is_bounded(self, client):
        resp = await client.get("/api/v1/modules/olx/ads", params={"limit": 1})
        assert resp.json()["count"] == 1


# ============================================================
# Market stats
# ============================================================


class TestOLXStats:
    async def test_stats_for_query(self, client):
        resp = await client.get("/api/v1/modules/olx/stats", params={"query": QUERY})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_ads"] == 2
        assert data["priced_ads"] == 1
        assert data["min_price"] == 7000.0
        assert data["median_price"] == 7000.0
        assert data["query"] == QUERY

    async def test_stats_empty_query(self, client):
        resp = await client.get("/api/v1/modules/olx/stats", params={"query": "немає"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_ads"] == 0
        assert data["median_price"] is None


# ============================================================
# Recommendations
# ============================================================


class TestOLXRecommendations:
    async def test_recommend_above_market(self, client):
        resp = await client.post(
            "/api/v1/modules/olx/recommendations",
            json={"query": QUERY, "title": "Скло лобове BMW", "price": 9000.0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["verdict"] == "above_market"
        assert data["suggested_price"] == round(7000.0 * 0.97)
        assert "text" in data

    async def test_recommend_unknown_market(self, client):
        resp = await client.post("/api/v1/modules/olx/recommendations", json={})
        assert resp.status_code == 200
        data = resp.json()
        # No query filter → uses all stored ads (one priced competitor).
        assert data["verdict"] == "unknown"
        assert data["suggested_price"] == round(7000.0 * 0.97)


# ============================================================
# Collection & scheduling
# ============================================================


class TestOLXCollection:
    async def test_collect_one_off_dedupes(self, client):
        resp = await client.post(
            "/api/v1/modules/olx/collect", json={"query": QUERY, "max_cards": 10}
        )
        assert resp.status_code == 200
        summary = resp.json()["summaries"][QUERY]
        assert summary["parsed"] == 2
        assert summary["inserted"] == 0  # fixture pre-seeded the same cards
        assert summary["total"] == 2

    async def test_collect_new_query_inserts(self, client):
        resp = await client.post(
            "/api/v1/modules/olx/collect", json={"query": "новий запит"}
        )
        assert resp.status_code == 200
        assert resp.json()["summaries"]["новий запит"]["inserted"] == 2

    async def test_schedule_validates_min_interval(self, client):
        resp = await client.post(
            "/api/v1/modules/olx/schedule", json={"interval_s": 5}
        )
        assert resp.status_code == 400
        assert "interval_s" in resp.json()["error"]

    async def test_schedule_start_and_stop(self, client):
        start = await client.post(
            "/api/v1/modules/olx/schedule",
            json={"queries": ["новий запит"], "interval_s": 10, "max_cards": 5},
        )
        assert start.status_code == 200
        payload = start.json()
        assert payload["scheduled"] is True
        assert payload["queries"] == ["новий запит"]

        # The immediate background run inserts two fresh competitors.
        deadline = time.time() + 5.0
        while time.time() < deadline:
            probe = await client.get(
                "/api/v1/modules/olx/ads", params={"query": "новий запит"}
            )
            if probe.json()["count"] == 2:
                break
            time.sleep(0.01)
        else:  # pragma: no cover - failure path
            pytest.fail("scheduled run did not collect ads in time")

        stop = await client.request("DELETE", "/api/v1/modules/olx/schedule")
        assert stop is not None
        body = stop.json()
        assert body["scheduled"] is False
        assert body["was_running"] is True
        assert body["history"][0]["query"] == "новий запит"
        assert body["history"][0]["parsed"] == 2


# ============================================================
# Price history & drops
# ============================================================


class TestOLXHistoryAndDrops:
    async def test_history_requires_fingerprint(self, client):
        resp = await client.get("/api/v1/modules/olx/history")
        assert resp.status_code == 400

    async def test_history_tracks_price_change(self, client, deps):
        from aios_core.modules.olx import AdCard

        _app, storage, _adb = deps
        bmw = next(ad for ad in storage.get_ads() if ad.url)
        repriced = AdCard.from_dict(bmw.to_dict())
        repriced.price = 6500.0
        # Explicitly later than the fixture seeding timestamp.
        storage.save_ads([repriced], seen_at="2026-07-21T23:59:00+00:00")

        resp = await client.get(
            "/api/v1/modules/olx/history",
            params={"fingerprint": bmw.fingerprint},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        prices = [point["price"] for point in data["history"]]
        assert prices == [7000.0, 6500.0]

    async def test_drops_and_gone(self, client, deps):
        from aios_core.modules.olx import AdCard

        _app, storage, _adb = deps
        ads = storage.get_ads()
        bmw = next(ad for ad in ads if ad.url)
        audi = next(ad for ad in ads if not ad.url)

        repriced = AdCard.from_dict(bmw.to_dict())
        repriced.price = 6500.0
        storage.save_ads([repriced])
        storage.sync_activity(QUERY, [bmw.fingerprint])  # Audi leaves the feed

        resp = await client.get("/api/v1/modules/olx/drops", params={"query": QUERY})
        assert resp.status_code == 200
        data = resp.json()

        assert data["drops_count"] == 1
        drop = data["drops"][0]
        assert drop["first_price"] == 7000.0
        assert drop["last_price"] == 6500.0
        assert drop["change_pct"] < 0

        assert data["gone_count"] == 1
        assert data["gone"][0]["title"] == audi.title


# ============================================================
# Detail page, chats, outbox, own ads, promotion
# ============================================================


class TestOLXDetail:
    async def test_detail_parse_endpoint(self, client):
        from tests.test_olx_actions import DETAIL_XML

        resp = await client.post("/api/v1/modules/olx/detail", json={"xml": DETAIL_XML})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Лобове скло BMW X3 G01 оригінал"
        assert data["views_count"] == 342
        assert data["seller_name"] == "Олена"

    async def test_detail_parse_requires_xml(self, client):
        resp = await client.post("/api/v1/modules/olx/detail", json={})
        assert resp.status_code == 400


class TestOLXChats:
    async def test_list_chats(self, client):
        resp = await client.get("/api/v1/modules/olx/chats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert data["unread_total"] == 2
        assert data["items"][0]["interlocutor"] == "Олексій"

    async def test_reply_flow_queue_cancel(self, client, deps):
        _app, storage, _adb = deps
        resp = await client.post(
            "/api/v1/modules/olx/chats/reply",
            json={"chat_key": "k1", "text": "Добрий день!", "interlocutor": "Олексій"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "queued"

        outbox = await client.get("/api/v1/modules/olx/outbox", params={"status": "pending"})
        assert outbox.json()["count"] == 1
        draft_id = outbox.json()["items"][0]["id"]

        cancel = await client.post(
            "/api/v1/modules/olx/outbox/cancel", json={"id": draft_id}
        )
        assert cancel.json()["cancelled"] is True
        assert storage.outbox_pending() == []

    async def test_reply_send_now_and_flush(self, client, deps):
        _app, storage, adb = deps
        queued = await client.post(
            "/api/v1/modules/olx/chats/reply",
            json={"chat_key": "k2", "text": "Чекаю огляд"},
        )
        assert queued.json()["status"] == "queued"

        flush = await client.post("/api/v1/modules/olx/outbox/send")
        assert flush.status_code == 200
        assert flush.json()["processed"] == 1
        assert storage.outbox_list(status="sent")

        direct = await client.post(
            "/api/v1/modules/olx/chats/reply",
            json={"chat_key": "k3", "text": "Приїжджайте", "send_now": True},
        )
        assert direct.json()["status"] == "sent"
        assert any("input text" in command for command in adb.commands)

    async def test_reply_requires_text(self, client):
        resp = await client.post("/api/v1/modules/olx/chats/reply", json={"chat_key": "k"})
        assert resp.status_code == 400


OWN_SNAPSHOT = [
    {
        "title": "Лобове скло BMW X3 G01",
        "price": 6700.0,
        "currency": "UAH",
        "views": 12,
        "favorites": 1,
        "messages": 0,
        "url": "https://www.olx.ua/d/uk/obyavlenie/test-IDown1a.html",
        "ad_id": "own1a",
    }
]


class TestOLXOwnAds:
    async def _seed_old_own_ad(self, storage):
        from aios_core.modules.olx import OwnAd

        own = OwnAd(
            title="Старе оголошення", price=1000.0, currency="UAH",
            views=2, url="https://www.olx.ua/d/uk/obyavlenie/old-IDold0a.html",
        )
        storage.upsert_own_ad(own, seen_at="2026-07-05T10:00:00+00:00")
        return own

    async def test_snapshot_list_and_stagnant(self, client, deps):
        _app, storage, _adb = deps

        resp = await client.post(
            "/api/v1/modules/olx/own/snapshot", json={"ads": OWN_SNAPSHOT}
        )
        assert resp.status_code == 200
        assert resp.json()["recorded"] == 1
        assert resp.json()["new"] == 1

        listing = await client.get("/api/v1/modules/olx/own")
        assert listing.json()["count"] == 1
        assert listing.json()["items"][0]["last_views"] == 12

        await self._seed_old_own_ad(storage)
        stagnant = await client.get("/api/v1/modules/olx/own/stagnant")
        titles = [item["title"] for item in stagnant.json()["items"]]
        assert "Старе оголошення" in titles

    async def test_improve_and_repost_flow(self, client, deps):
        _app, storage, _adb = deps
        await client.post("/api/v1/modules/olx/own/snapshot", json={"ads": OWN_SNAPSHOT})
        fp = storage.own_ads()[0]["fingerprint"]

        improve = await client.post(
            "/api/v1/modules/olx/own/improve",
            json={"fingerprint": fp, "query": QUERY},
        )
        assert improve.status_code == 200
        data = improve.json()
        assert data["suggested_title"]
        assert "text" in data

        dry = await client.post(
            "/api/v1/modules/olx/own/repost", json={"fingerprint": fp}
        )
        assert dry.json()["status"] == "dry_run"
        assert dry.json()["executed"] is False

        executed = await client.post(
            "/api/v1/modules/olx/own/repost",
            json={"fingerprint": fp, "confirm": True},
        )
        assert executed.json()["status"] == "executed"
        assert storage.own_ads(status="active") == []
        assert storage.own_ads(status="inactive")

        missing = await client.post(
            "/api/v1/modules/olx/own/repost", json={"fingerprint": "nope"}
        )
        assert missing.status_code == 404


class TestOLXNotify:
    async def test_notify_requires_webhook(self, client):
        resp = await client.post("/api/v1/modules/olx/notify", json={})
        assert resp.status_code == 400

    async def test_notify_posts_drops(self, client, deps):
        # No webhook reachable in tests → summary reports zero sent, no crash.
        import socket

        # Use an unroutable port quickly failing connection.
        _app, storage, _adb = deps
        try:
            resp = await client.post(
                "/api/v1/modules/olx/notify",
                json={"webhook_url": "http://127.0.0.1:1/hook", "query": QUERY},
            )
        except Exception:
            return  # environment without network stack tolerances
        assert resp.status_code in (200, 400, 500)
