"""Processes view."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get


async def _get_processes() -> dict:
    return await get("/api/processes")


def render() -> None:
    ui.label("Processes").classes("text-h6")

    processes_label = ui.label("Loading processes...").classes("text-body1")
    process_table = ui.table(
        columns=[
            {"name": "id", "label": "ID", "field": "id"},
            {"name": "name", "label": "Name", "field": "name"},
            {"name": "status", "label": "Status", "field": "status"},
            {"name": "agent_id", "label": "Agent", "field": "agent_id"},
            {"name": "created_at", "label": "Created", "field": "created_at"},
        ],
        rows=[],
    ).classes("w-full")

    async def load_processes() -> None:
        data = await _get_processes()
        processes = data.get("processes", [])
        processes_label.set_text(f"Processes: {len(processes)}")
        process_table.rows = [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "status": p.get("status"),
                "agent_id": p.get("agent_id"),
                "created_at": p.get("created_at"),
            }
            for p in processes
        ]

    ui.button("Refresh processes", on_click=load_processes).props("flat")
