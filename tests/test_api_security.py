"""Regression tests for API authentication, authorization and shared runtime state."""

import pytest
from httpx import ASGITransport, AsyncClient

from aios_core.api.app import create_app


@pytest.mark.asyncio
async def test_api_fails_closed_without_configured_keys():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/health")).status_code == 200
        response = await client.get("/api/v1/stats")
        assert response.status_code == 503


@pytest.mark.asyncio
async def test_role_guard_and_rest_mcp_share_database():
    keys = {
        "viewer-key": {"subject": "viewer", "roles": ["viewer"]},
        "writer-key": {"subject": "writer", "roles": ["writer"]},
    }
    app = create_app(api_keys=keys)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        viewer = {"Authorization": "Bearer viewer-key"}
        writer = {"Authorization": "Bearer writer-key"}
        assert (
            await client.post("/api/v1/memory", json={"content": {"a": 1}}, headers=viewer)
        ).status_code == 403
        saved = await client.post("/api/v1/memory", json={"content": {"a": 1}}, headers=writer)
        assert saved.status_code == 201
        rpc = await client.post(
            "/rpc",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "aios_memory_search", "arguments": {"query": "a"}},
            },
            headers=writer,
        )
        assert rpc.status_code == 200
        assert '"count": 1' in rpc.json()["result"]["content"][0]["text"]


@pytest.mark.asyncio
async def test_personal_memory_is_isolated_by_authenticated_subject():
    keys = {
        "alice-key": {"subject": "alice", "roles": ["writer"]},
        "bob-key": {"subject": "bob", "roles": ["writer"]},
    }
    app = create_app(api_keys=keys)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        alice = {"Authorization": "Bearer alice-key"}
        bob = {"Authorization": "Bearer bob-key"}
        saved = await client.post(
            "/api/v1/memory",
            json={"content": {"private": "alice only"}, "category": "personal"},
            headers=alice,
        )
        assert saved.status_code == 201
        item_id = saved.json()["id"]
        assert (await client.get(f"/api/v1/memory/{item_id}", headers=bob)).status_code == 404
        result = await client.get("/api/v1/memory?category=personal", headers=bob)
        assert result.json()["count"] == 0
        assert (await client.get(f"/api/v1/memory/{item_id}", headers=alice)).status_code == 200


@pytest.mark.asyncio
async def test_tasks_are_scoped_to_the_creating_subject():
    keys = {
        "alice-key": {"subject": "alice", "roles": ["writer"]},
        "bob-key": {"subject": "bob", "roles": ["writer"]},
    }
    app = create_app(api_keys=keys)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        alice = {"Authorization": "Bearer alice-key"}
        bob = {"Authorization": "Bearer bob-key"}
        created = await client.post("/api/v1/tasks", json={"name": "alice-task"}, headers=alice)
        task_id = created.json()["task_id"]
        assert (await client.get(f"/api/v1/tasks/{task_id}", headers=bob)).status_code == 404
        assert (await client.get("/api/v1/tasks", headers=bob)).json()["count"] == 0


@pytest.mark.asyncio
async def test_approver_role_is_required_for_approval_actions():
    keys = {
        "writer-key": {"subject": "writer", "roles": ["writer"]},
        "approver-key": {"subject": "reviewer", "roles": ["approver"]},
    }
    app = create_app(api_keys=keys)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        writer = {"Authorization": "Bearer writer-key"}
        result = await client.post("/api/v1/approvals/not-a-real-id/approve", headers=writer)
        assert result.status_code == 403
        result = await client.post(
            "/api/v1/approvals/not-a-real-id/approve",
            headers={"Authorization": "Bearer approver-key"},
        )
        assert result.status_code == 404


def test_api_key_configuration_rejects_empty_or_non_string_roles():
    from aios_core.api.security import load_api_keys

    with pytest.raises(ValueError, match="non-empty list of role strings"):
        load_api_keys('{"key":{"subject":"operator","roles":[]}}')
    with pytest.raises(ValueError, match="non-empty list of role strings"):
        load_api_keys('{"key":{"subject":"operator","roles":[1]}}')


@pytest.mark.asyncio
async def test_health_and_api_documentation_are_public_but_api_remains_closed():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/health")).status_code == 200
        assert (await client.get("/docs")).status_code == 200
        assert (await client.get("/openapi.json")).status_code == 200
        assert (await client.get("/api/v1/stats")).status_code == 503


@pytest.mark.asyncio
async def test_task_rate_limit_is_scoped_to_authenticated_subject(monkeypatch):
    from aios_core.api.mixins_core import rate_limiter

    rate_limiter.reset()
    rate_limiter.set_tier("alice", 1)
    try:
        keys = {
            "alice-key": {"subject": "alice", "roles": ["writer"]},
            "bob-key": {"subject": "bob", "roles": ["writer"]},
        }
        app = create_app(api_keys=keys)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            alice = {"Authorization": "Bearer alice-key"}
            bob = {"Authorization": "Bearer bob-key"}
            assert (await client.post("/api/v1/tasks", json={"name": "one"}, headers=alice)).status_code == 200
            blocked = await client.post("/api/v1/tasks", json={"name": "two"}, headers=alice)
            assert blocked.status_code == 429
            assert blocked.headers["retry-after"] == str(rate_limiter.window_seconds)
            assert (await client.post("/api/v1/tasks", json={"name": "bob"}, headers=bob)).status_code == 200
    finally:
        rate_limiter.reset()


@pytest.mark.asyncio
async def test_openapi_includes_every_registered_http_route():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        spec = (await client.get("/openapi.json")).json()
    documented = set(spec["paths"])
    runtime = {route.path for route in app.routes if getattr(route, "methods", None)}
    assert runtime <= documented
    assert "security" not in spec["paths"]["/health"]["get"]
    assert spec["paths"]["/api/v1/tasks"]["post"]["security"] == [{"ApiKeyAuth": []}]


@pytest.mark.asyncio
async def test_admin_routes_are_registered_and_require_admin_role():
    from aios_core.api.security import required_roles

    assert required_roles("/api/v1/admin/keys", "GET") == {"admin"}
    keys = {
        "writer-key": {"subject": "writer", "roles": ["writer"]},
        "admin-key": {"subject": "admin", "roles": ["admin"]},
    }
    app = create_app(api_keys=keys)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/api/v1/admin/keys", headers={"Authorization": "Bearer writer-key"})).status_code == 403
        assert (await client.get("/api/v1/admin/keys", headers={"Authorization": "Bearer admin-key"})).status_code == 200


def test_bearer_lookup_uses_configured_principal():
    from aios_core.api.security import Principal, find_principal

    keys = {"correct-token": Principal("operator", frozenset({"viewer"}))}
    assert find_principal(keys, "correct-token").subject == "operator"
    assert find_principal(keys, "wrong-token") is None


@pytest.mark.asyncio
async def test_admin_internal_errors_do_not_expose_server_details():
    app = create_app(api_keys={"admin-key": {"subject": "admin", "roles": ["admin"]}})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/admin/import",
            json={"input": "/definitely/not/a/real/import.json"},
            headers={"Authorization": "Bearer admin-key"},
        )
    assert response.status_code == 400
    assert response.json() == {"error": "File path does not exist or is not accessible"}


def test_admin_data_path_is_confined_when_operator_root_is_configured(monkeypatch, tmp_path):
    from aios_core.api.admin_routes import _validated_data_path

    monkeypatch.setenv("AIOS_ADMIN_DATA_DIR", str(tmp_path))
    assert _validated_data_path(str(tmp_path / "export.json")).startswith(str(tmp_path))
    with pytest.raises(ValueError, match="AIOS_ADMIN_DATA_DIR"):
        _validated_data_path("/tmp/outside.json")


@pytest.mark.asyncio
async def test_admin_import_rejects_unsupported_type_before_processing(tmp_path):
    source = tmp_path / "input.json"
    source.write_text("[]")
    app = create_app(api_keys={"admin-key": {"subject": "admin", "roles": ["admin"]}})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/admin/import",
            json={"type": "memory", "input": str(source)},
            headers={"Authorization": "Bearer admin-key"},
        )
    assert response.status_code == 400
    assert response.json()["error"] == "Only tasks import is supported"


@pytest.mark.asyncio
async def test_admin_export_rejects_non_numeric_limit():
    app = create_app(api_keys={"admin-key": {"subject": "admin", "roles": ["admin"]}})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/admin/export",
            json={"type": "memory", "limit": "1; DROP TABLE personal_memory"},
            headers={"Authorization": "Bearer admin-key"},
        )
    assert response.status_code == 400
    assert response.json()["error"] == "limit must be an integer between 1 and 100000"


@pytest.mark.asyncio
async def test_sensitive_admin_operations_have_principal_scoped_rate_limit():
    from aios_core.rate_limiter import rate_limiter

    path = "/api/v1/admin/keys/generate"
    rate_limiter.reset()
    rate_limiter.set_tier(f"sensitive:admin:{path}", 1)
    try:
        app = create_app(api_keys={"admin-key": {"subject": "admin", "roles": ["admin"]}})
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = {"Authorization": "Bearer admin-key"}
            first = await client.post(path, json={"subject": "one", "roles": ["viewer"]}, headers=headers)
            blocked = await client.post(path, json={"subject": "two", "roles": ["viewer"]}, headers=headers)
        assert first.status_code == 200
        assert blocked.status_code == 429
        assert blocked.headers["retry-after"] == str(rate_limiter.window_seconds)
    finally:
        rate_limiter.reset()
