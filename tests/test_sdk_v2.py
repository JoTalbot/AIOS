"""SDK v4.2.0 tests"""

import pytest
from sdk.aios_sdk import AIOSClient, AIOSClientSync

def test_client_init():
    client = AIOSClient(base_url="http://localhost:8000", api_key="test-key")
    assert client.base_url == "http://localhost:8000"
    assert "Bearer test-key" in client.headers["Authorization"]

def test_client_url():
    client = AIOSClient(base_url="http://localhost:8000/")
    assert client._url("/health") == "http://localhost:8000/health"
    assert client.base_url == "http://localhost:8000"

def test_sync_wrapper():
    sync_client = AIOSClientSync(base_url="http://localhost:8000", api_key="test")
    assert sync_client.base_url == "http://localhost:8000"
    assert hasattr(sync_client, "health")
    assert hasattr(sync_client, "stats")
    assert hasattr(sync_client, "advisor_draft_reply")

def test_async_methods_exist():
    client = AIOSClient()
    # Check all expected methods from v4.2.0 exist
    expected = [
        "health", "ready", "stats", "metrics",
        "create_task", "list_tasks", "get_task", "evaluate",
        "propose_evolution", "list_proposals",
        "memory_store", "memory_search",
        "kg_add_node", "kg_query",
        "android_list_devices", "android_device_status",
        "apps_list", "apps_get",
        "shards_stats", "shards_jobs",
        "marketplace_search", "marketplace_publish", "marketplace_plugins",
        "advisor_draft_reply", "advisor_summarize_inbox", "advisor_price_advice",
        "watch_events"
    ]
    for method in expected:
        assert hasattr(client, method), f"Missing method {method}"

def test_sync_methods_mirrored():
    sync_client = AIOSClientSync()
    expected_sync = [
        "health", "stats", "metrics",
        "create_task", "list_tasks", "get_task", "evaluate",
        "memory_store", "memory_search",
        "android_list_devices", "apps_list",
        "marketplace_search", "marketplace_plugins",
        "advisor_draft_reply"
    ]
    for method in expected_sync:
        assert hasattr(sync_client, method), f"Missing sync method {method}"

@pytest.mark.asyncio
async def test_client_health_mock(monkeypatch):
    # Mock httpx to avoid real network
    class MockResp:
        def raise_for_status(self): pass
        def json(self): return {"status": "ok"}
        @property
        def text(self): return "metrics"
    
    class MockClient:
        def __init__(self, timeout=None): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url, headers=None, params=None): return MockResp()
        async def post(self, url, json=None, headers=None): return MockResp()

    monkeypatch.setattr("httpx.AsyncClient", MockClient)
    client = AIOSClient()
    result = await client.health()
    assert result["status"] == "ok"
