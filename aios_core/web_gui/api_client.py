"""Async client for AIOS backend API."""

from __future__ import annotations

import os
from typing import Any

import httpx

_BASE_URL = os.getenv("AIOS_API_URL", "http://aios-api:8000")
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def _request(method: str, path: str, **kwargs: Any) -> Any:
    async with httpx.AsyncClient(base_url=_BASE_URL, timeout=_TIMEOUT) as client:
        resp = await client.request(method, path, **kwargs)
        resp.raise_for_status()
        return resp.json()


async def get(path: str, params: dict | None = None) -> Any:
    return await _request("GET", path, params=params)


async def post(path: str, json: dict | None = None) -> Any:
    return await _request("POST", path, json=json)


# Convenience wrappers for existing endpoints


async def get_stats() -> dict:
    return await get("/api/v1/stats")


async def get_services() -> dict:
    return await get("/api/v1/services")


async def service_action(service: str, action: str) -> dict:
    return await post("/api/v1/service/action", json={"service": service, "action": action})


async def get_android_devices() -> dict:
    return await get("/api/v1/android/devices")


async def get_auto_study_status() -> dict:
    return await get("/api/v1/auto-study/status")


async def start_auto_study(package: str = "ua.slando", scenario: str = "basic_explore") -> dict:
    return await post(
        "/api/v1/auto-study",
        json={"package": package, "scenario": scenario},
    )


async def get_auto_study_history() -> dict:
    return await get("/api/v1/auto-study/history")


async def get_backups() -> dict:
    return await get("/api/v1/backups")


async def create_backup(label: str = "dashboard") -> dict:
    return await post("/api/v1/backups", json={"action": "create", "label": label})


async def verify_backup(backup_id: str) -> dict:
    return await post("/api/v1/backups", json={"action": "verify", "backup_id": backup_id})


async def get_constitution() -> dict:
    return await get("/api/v1/constitution")


async def get_constitution_article(number: int) -> dict:
    return await get(f"/api/v1/constitution/{number}")


async def get_knowledge_graph() -> dict:
    return await get("/api/v1/knowledge-graph")


async def get_models() -> dict:
    return await get("/api/v1/models")


async def cycle_model_stage(name: str, stage: str) -> dict:
    return await post(f"/api/v1/models/{name}/stage", json={"stage": stage})


async def get_agents() -> dict:
    return await get("/api/v1/agents")
