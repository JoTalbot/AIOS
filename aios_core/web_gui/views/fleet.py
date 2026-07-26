"""Fleet management view."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get


def render() -> None:
    ui.label("Fleet").classes("text-h6")

    fleet_label = ui.label("Fleet: loading...").classes("text-body1")

    async def load_fleet() -> None:
        data = await get("/api/fleet")
        fleet = data.get("fleet", [])
        fleet_label.set_text(f"Devices: {len(fleet)}")
        table.rows = [
            {
                "device_id": d.get("device_id"),
                "status": d.get("status"),
                "package": d.get("package"),
            }
            for d in fleet
        ]

    ui.button("Refresh fleet", on_click=load_fleet).props("flat")

    columns = [
        {"name": "device_id", "label": "Device ID", "field": "device_id"},
        {"name": "status", "label": "Status", "field": "status"},
        {"name": "package", "label": "Package", "field": "package"},
    ]
    table = ui.table(columns=columns, rows=[]).classes("w-full")
