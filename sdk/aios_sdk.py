"""AIOS Python SDK v4.0.0-alpha

Official client library for interacting with AIOS instances.
"""

import httpx
from typing import Any, Dict, Optional


class AIOSClient:
    """High-level client for AIOS REST API."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    async def health(self) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/health", headers=self.headers)
            return resp.json()

    async def stats(self) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/api/v1/stats", headers=self.headers)
            return resp.json()

    async def create_task(self, name: str, description: str = "", **kwargs) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/tasks",
                json={"name": name, "description": description, **kwargs},
                headers=self.headers
            )
            return resp.json()

    async def evaluate(self, action: dict) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/evaluate",
                json=action,
                headers=self.headers
            )
            return resp.json()

    async def propose_evolution(self, change: dict, component: str, reason: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/evolution/proposals",
                json={"change": change, "component": component, "reason": reason},
                headers=self.headers
            )
            return resp.json()


# Synchronous wrapper
class AIOSClientSync:
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.async_client = AIOSClient(base_url, api_key)

    def health(self):
        import asyncio
        return asyncio.run(self.async_client.health())

    def stats(self):
        import asyncio
        return asyncio.run(self.async_client.stats())