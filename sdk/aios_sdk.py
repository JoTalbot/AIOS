"""AIOS Python SDK v4.2.0 - Official client library

H3.12: Full REST + WS + Marketplace + Android + AI Advisor client
Examples: "your agent in 30 lines" per roadmap.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional

import httpx


class AIOSClient:
    """High-level async client for AIOS REST API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    # --- Core ---

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/health"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def ready(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/ready"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def stats(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/v1/stats"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def metrics(self) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/metrics"), headers=self.headers)
            resp.raise_for_status()
            return resp.text

    # --- Tasks / Orchestrator ---

    async def create_task(self, name: str, description: str = "", **kwargs) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/v1/tasks"),
                json={"name": name, "description": description, **kwargs},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def list_tasks(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/v1/tasks"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def get_task(self, task_id: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url(f"/api/v1/tasks/{task_id}"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def evaluate(self, action: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/v1/evaluate"), json=action, headers=self.headers
            )
            resp.raise_for_status()
            return resp.json()

    # --- Evolution ---

    async def propose_evolution(self, change: dict, component: str, reason: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/v1/evolution/proposals"),
                json={"change": change, "component": component, "reason": reason},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def list_proposals(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/v1/evolution/proposals"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    # --- Memory ---

    async def memory_store(
        self, content: dict, category: str = "operational", tags: Optional[List[str]] = None
    ) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/v1/memory"),
                json={"content": content, "category": category, "tags": tags or []},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def memory_search(self, query: str, category: str = "", limit: int = 20) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                self._url(f"/api/v1/memory/search"),
                params={"query": query, "category": category, "limit": limit},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    # --- Knowledge Graph ---

    async def kg_add_node(
        self, label: str, node_type: str = "entity", properties: Optional[dict] = None
    ) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/v1/kg/nodes"),
                json={"label": label, "type": node_type, "properties": properties or {}},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def kg_query(self, query: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                self._url("/api/v1/kg/query"), params={"q": query}, headers=self.headers
            )
            resp.raise_for_status()
            return resp.json()

    # --- Android / Platforms ---

    async def android_list_devices(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/v1/android/devices"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def android_device_status(self, device_id: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                self._url(f"/api/v1/android/devices/{device_id}"), headers=self.headers
            )
            resp.raise_for_status()
            return resp.json()

    async def apps_list(self, platform: str = "") -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                self._url("/api/v1/apps"), params={"platform": platform}, headers=self.headers
            )
            resp.raise_for_status()
            return resp.json()

    async def apps_get(self, platform: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url(f"/api/v1/apps/{platform}"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    # --- Shards / Fleet ---

    async def shards_stats(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/v1/shards/stats"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def shards_jobs(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self._url("/api/v1/shards/jobs"), headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    # --- Marketplace ---

    async def marketplace_search(self, query: str = "", tag: str = "", limit: int = 20) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                self._url("/api/v1/marketplace/search"),
                params={"query": query, "tag": tag, "limit": limit},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def marketplace_publish(self, name: str, description: str, **kwargs) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/v1/marketplace/publish"),
                json={"name": name, "description": description, **kwargs},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def marketplace_plugins(self, platform: str = "") -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                self._url("/api/v1/marketplace/plugins"),
                params={"platform": platform},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    # --- AI Advisor (H3.11) ---

    async def advisor_draft_reply(
        self,
        platform: str,
        original_message: str,
        recipient: str,
        item_context: Optional[dict] = None,
    ) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/v1/advisor/draft"),
                json={
                    "platform": platform,
                    "original_message": original_message,
                    "recipient": recipient,
                    "item_context": item_context or {},
                },
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def advisor_summarize_inbox(self, platform: str, messages: List[dict]) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self._url("/api/v1/advisor/summarize"),
                json={"platform": platform, "messages": messages},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def advisor_price_advice(self, platform: str, item_id: str, current_price: float) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                self._url("/api/v1/advisor/price"),
                params={"platform": platform, "item_id": item_id, "current_price": current_price},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    # --- WebSocket helpers ---

    async def watch_events(
        self, on_event: Callable[[dict], None], channels: Optional[List[str]] = None
    ):
        """Watch events via WebSocket."""
        try:
            import websockets

            uri = (
                self.base_url.replace("http://", "ws://").replace("https://", "wss://")
                + "/ws/events"
            )
            async with websockets.connect(uri, extra_headers=self.headers) as ws:
                if channels:
                    await ws.send(json.dumps({"subscribe": channels}))
                async for msg in ws:
                    try:
                        data = json.loads(msg)
                        on_event(data)
                    except Exception:
                        on_event({"raw": msg})
        except ImportError:
            raise RuntimeError("websockets package required for watch_events")


# Synchronous wrapper with all methods mirrored
class AIOSClientSync:
    """Sync wrapper - use in scripts without asyncio."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self._async = AIOSClient(base_url, api_key)
        self.base_url = self._async.base_url

    def _run(self, coro):
        return asyncio.run(coro)

    # Core
    def health(self):
        return self._run(self._async.health())

    def ready(self):
        return self._run(self._async.ready())

    def stats(self):
        return self._run(self._async.stats())

    def metrics(self):
        return self._run(self._async.metrics())

    # Tasks
    def create_task(self, *a, **kw):
        return self._run(self._async.create_task(*a, **kw))

    def list_tasks(self):
        return self._run(self._async.list_tasks())

    def get_task(self, task_id: str):
        return self._run(self._async.get_task(task_id))

    def evaluate(self, action: dict):
        return self._run(self._async.evaluate(action))

    # Evolution
    def propose_evolution(self, *a, **kw):
        return self._run(self._async.propose_evolution(*a, **kw))

    def list_proposals(self):
        return self._run(self._async.list_proposals())

    # Memory
    def memory_store(self, *a, **kw):
        return self._run(self._async.memory_store(*a, **kw))

    def memory_search(self, *a, **kw):
        return self._run(self._async.memory_search(*a, **kw))

    # KG
    def kg_add_node(self, *a, **kw):
        return self._run(self._async.kg_add_node(*a, **kw))

    def kg_query(self, query: str):
        return self._run(self._async.kg_query(query))

    # Android
    def android_list_devices(self):
        return self._run(self._async.android_list_devices())

    def android_device_status(self, device_id: str):
        return self._run(self._async.android_device_status(device_id))

    def apps_list(self, platform: str = ""):
        return self._run(self._async.apps_list(platform))

    def apps_get(self, platform: str):
        return self._run(self._async.apps_get(platform))

    # Shards
    def shards_stats(self):
        return self._run(self._async.shards_stats())

    def shards_jobs(self):
        return self._run(self._async.shards_jobs())

    # Marketplace
    def marketplace_search(self, *a, **kw):
        return self._run(self._async.marketplace_search(*a, **kw))

    def marketplace_publish(self, *a, **kw):
        return self._run(self._async.marketplace_publish(*a, **kw))

    def marketplace_plugins(self, *a, **kw):
        return self._run(self._async.marketplace_plugins(*a, **kw))

    # Advisor
    def advisor_draft_reply(self, *a, **kw):
        return self._run(self._async.advisor_draft_reply(*a, **kw))

    def advisor_summarize_inbox(self, *a, **kw):
        return self._run(self._async.advisor_summarize_inbox(*a, **kw))

    def advisor_price_advice(self, *a, **kw):
        return self._run(self._async.advisor_price_advice(*a, **kw))


# Example: "agent in 30 lines"
def example_agent():
    """
    Example usage:

    from sdk.aios_sdk import AIOSClientSync

    client = AIOSClientSync("http://localhost:8000", api_key="local-dev")

    print(client.health())
    print(client.stats())

    # Create a task
    task = client.create_task("analyze_trends", "Analyze OLX trends for iPhone")
    print(task)

    # Draft reply via AI Advisor
    draft = client.advisor_draft_reply(
        platform="olx",
        original_message="Какая последняя цена? Торг уместен?",
        recipient="buyer123",
        item_context={"title": "iPhone 13 128GB", "price": 22000}
    )
    print(draft)

    # Search marketplace
    results = client.marketplace_search(query="olx")
    print(results)
    """
    pass
