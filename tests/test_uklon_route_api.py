from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from aios_core.api.app import create_app


@pytest.mark.asyncio
async def test_route_draft_api_preserves_pickup_stops_and_final(monkeypatch, tmp_path):
    monkeypatch.setenv("AIOS_PROJECT_ROOT", str(tmp_path))
    keys = {
        "writer-key": {"subject": "writer", "roles": ["writer"]},
        "viewer-key": {"subject": "viewer", "roles": ["viewer"]},
    }
    app = create_app(db_path=":memory:", api_keys=keys)
    writer = {"Authorization": "Bearer writer-key"}
    viewer = {"Authorization": "Bearer viewer-key"}
    payload = {
        "pickup": "Точка А",
        "stops": ["Точка Б", {"address": "Точка В"}],
        "final_destination": "Точка Г",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/api/v1/phone/uklon/route-drafts", json=payload, headers=writer)
        assert created.status_code == 201
        body = created.json()
        assert body["status"] == "route_draft_created"
        assert body["booking"] == "not_created"
        assert body["stop_count"] == 2
        assert body["route"]["pickup"] == "Точка А"
        assert body["route"]["final_destination"] == "Точка Г"
        assert body["route"]["route_points"] == ["Точка Б", "Точка В", "Точка Г"]

        draft_id = body["draft_id"]
        loaded = await client.get(f"/api/v1/phone/uklon/route-drafts/{draft_id}", headers=writer)
        assert loaded.status_code == 200
        assert loaded.json()["route"]["stops"][1]["address"] == "Точка В"
        forbidden = await client.get(f"/api/v1/phone/uklon/route-drafts/{draft_id}", headers=viewer)
        assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_route_draft_api_fails_closed_when_auth_is_disabled(tmp_path):
    app = create_app(db_path=":memory:", auth_required=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/phone/uklon/route-drafts",
            json={"pickup": "A", "final_destination": "B"},
        )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_route_draft_api_rejects_invalid_stops(monkeypatch, tmp_path):
    monkeypatch.setenv("AIOS_PROJECT_ROOT", str(tmp_path))
    app = create_app(
        db_path=":memory:",
        api_keys={"writer-key": {"subject": "writer", "roles": ["writer"]}},
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/phone/uklon/route-drafts",
            json={"final_destination": "B", "stops": "not-a-list"},
            headers={"Authorization": "Bearer writer-key"},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_route_draft_lifecycle_list_status_cancel_delete(monkeypatch, tmp_path):
    monkeypatch.setenv("AIOS_PROJECT_ROOT", str(tmp_path))
    app = create_app(
        db_path=":memory:",
        api_keys={"writer-key": {"subject": "writer", "roles": ["writer"]}},
    )
    headers = {"Authorization": "Bearer writer-key"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        status = await client.get("/api/v1/phone/uklon/status", headers=headers)
        assert status.status_code == 200
        assert status.json()["booking_automation"] is False

        created = await client.post(
            "/api/v1/phone/uklon/route-drafts",
            json={"pickup": "A", "final_destination": "B"},
            headers=headers,
        )
        draft_id = created.json()["draft_id"]
        listed = await client.get("/api/v1/phone/uklon/route-drafts", headers=headers)
        assert listed.status_code == 200
        assert listed.json()["count"] == 1

        cancelled = await client.post(
            f"/api/v1/phone/uklon/route-drafts/{draft_id}/cancel", headers=headers
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["state"] == "cancelled"

        deleted = await client.delete(
            f"/api/v1/phone/uklon/route-drafts/{draft_id}", headers=headers
        )
        assert deleted.status_code == 204
        missing = await client.get(
            f"/api/v1/phone/uklon/route-drafts/{draft_id}", headers=headers
        )
        assert missing.status_code == 404
