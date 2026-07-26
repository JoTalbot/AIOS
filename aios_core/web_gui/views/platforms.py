"""Platforms view."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get


def render() -> None:
    ui.label("Platforms").classes("text-h6")

    platforms_label = ui.label("Platforms: loading...").classes("text-body1")

    async def load_platforms() -> None:
        data = await get("/api/platforms")
        platforms = data.get("platforms", [])
        platforms_label.set_text(f"Platforms: {len(platforms)}")
        table.rows = [
            {
                "name": p.get("name"),
                "version": p.get("version"),
                "status": p.get("status"),
            }
            for p in platforms
        ]

    ui.button("Refresh platforms", on_click=load_platforms).props("flat")

    columns = [
        {"name": "name", "label": "Name", "field": "name"},
        {"name": "version", "label": "Version", "field": "version"},
        {"name": "status", "label": "Status", "field": "status"},
    ]
    table = ui.table(columns=columns, rows=[]).classes("w-full")
