"""Services management view with detailed actions."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get


async def _get_services() -> dict:
    return await get("/api/services")


def render() -> None:
    ui.label("Services").classes("text-h6")

    service_table = ui.table(
        columns=[
            {"name": "name", "label": "Name", "field": "name"},
            {"name": "status", "label": "Status", "field": "status"},
            {"name": "uptime", "label": "Uptime", "field": "uptime"},
            {"name": "pid", "label": "PID", "field": "pid"},
            ],
        rows=[],
    ).classes("w-full")

    async def load_services() -> None:
        data = await _get_services()
        services = data.get("services", [])
        service_table.rows = [
            {
                "name": s.get("name"),
                "status": s.get("status"),
                "uptime": s.get("uptime", "N/A"),
                "pid": s.get("pid", "N/A"),
            }
            for s in services
        ]

    ui.label("Перезапуск служб хоста намеренно отключён в публичной панели.").classes("text-caption text-warning")
    ui.button("Refresh services", on_click=load_services).props("flat")
