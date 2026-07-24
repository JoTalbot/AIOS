import pytest
from httpx import ASGITransport, AsyncClient

from aios_core.api.app import create_app


@pytest.mark.asyncio
async def test_invalid_json_returns_400_not_internal_error():
    app = create_app(auth_required=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/memory", content=b"{not-json", headers={"content-type": "application/json"}
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_memory_limits_are_bounded():
    app = create_app(auth_required=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/memory?limit=-1")
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.asyncio
async def test_api_responses_include_baseline_security_headers():
    app = create_app(auth_required=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["content-security-policy"] == "frame-ancestors 'none'"


@pytest.mark.asyncio
async def test_request_id_is_returned_and_safe_client_value_is_preserved():
    app = create_app(auth_required=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health", headers={"X-Request-ID": "trace-123"})
        generated = await client.get("/health", headers={"X-Request-ID": "bad\nvalue"})
    assert response.headers["x-request-id"] == "trace-123"
    assert generated.headers["x-request-id"] != "bad\nvalue"
    assert generated.headers["x-request-id"]
