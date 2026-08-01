"""Services management view with detailed actions."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get, post


async def _get_services() -> dict:
    return await get("/api/services")


async def _service_action(service: str, action: str) -> dict:
    return await post("/api/service/action", json={"service": service, "action": action})


def render() -> None:
    ui.label("Services").classes("text-h6")

    service_table = ui.table(
        columns=[
            {"name": "name", "label": "Name", "field": "name"},
            {"name": "status", "label": "Status", "field": "status"},
            {"name": "uptime", "label": "Uptime", "field": "uptime"},
            {"name": "pid", "label": "PID", "field": "pid"},
            {"name": "actions", "label": "Actions", "field": "actions"},
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
                "actions": ui.button(
                    "Restart",
                    on_click=lambda svc=s.get("name"): restart_service(svc),  # noqa: B008  # идиома захвата loop var
                ),
            }
            for s in services
        ]

    async def restart_service(name: str) -> None:
        result = await _service_action(name, "restart")
        if result.get("ok"):
            ui.notify(f"Restarted {name}", type="positive")
        else:
            ui.notify(f"Restart failed for {name}: {result.get('error', 'unknown error')}", type="negative")
        await load_services()

    ui.button("Refresh services", on_click=load_services).props("flat")
