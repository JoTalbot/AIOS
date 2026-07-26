"""Audit log view."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get


async def _get_audit_events(limit: int = 50) -> dict:
    return await get("/api/audit", params={"limit": str(limit)})


def render() -> None:
    ui.label("Audit").classes("text-h6")

    limit_input = ui.input("Limit", value="50").classes("w-32")
    table = ui.table(
        columns=[
            {"name": "ts", "label": "Time", "field": "ts"},
            {"name": "type", "label": "Type", "field": "type"},
            {"name": "actor", "label": "Actor", "field": "actor"},
            {"name": "action", "label": "Action", "field": "action"},
            {"name": "severity", "label": "Severity", "field": "severity"},
            {"name": "detail", "label": "Detail", "field": "detail"},
        ],
        rows=[],
    ).classes("w-full")

    async def load_audit() -> None:
        try:
            limit = int(limit_input.value or "50")
        except (TypeError, ValueError):
            limit = 50
        data = await _get_audit_events(limit=limit)
        events = data.get("events", [])
        table.rows = [
            {
                "ts": e.get("ts"),
                "type": e.get("type"),
                "actor": e.get("actor"),
                "action": e.get("action"),
                "severity": e.get("severity"),
                "detail": e.get("detail"),
            }
            for e in events
        ]

    ui.button("Refresh audit", on_click=load_audit).props("flat")
