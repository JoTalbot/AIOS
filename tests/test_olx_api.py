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

    storage = OLXStorage(":memory:")
    storage.save_ads(CardParser().parse(SAMPLE_XML, query=QUERY))
    collector = FakeCollector()
    api = AIOSAPI(
        db_path=":memory:",
        constitution_dir=CONSTITUTION_DIR,
        policies_dir=POLICIES_DIR,
        auth_required=False,
        olx_storage=storage,
        olx_collector=collector,
    )
    return api.create_starlette_app(), storage


@pytest.fixture
async def client(deps):
    app, _storage = deps
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

        _app, storage = deps
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

        _app, storage = deps
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
