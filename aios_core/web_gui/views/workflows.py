"""Workflows view."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get


async def _get_workflows() -> dict:
    return await get("/api/workflows")


def render() -> None:
    ui.label("Workflows").classes("text-h6")

    workflows_label = ui.label("Loading workflows...").classes("text-body1")
    workflow_table = ui.table(
        columns=[
            {"name": "id", "label": "ID", "field": "id"},
            {"name": "name", "label": "Name", "field": "name"},
            {"name": "status", "label": "Status", "field": "status"},
            {"name": "steps", "label": "Steps", "field": "steps"},
            {"name": "created_at", "label": "Created", "field": "created_at"},
        ],
        rows=[],
    ).classes("w-full")

    async def load_workflows() -> None:
        data = await _get_workflows()
        workflows = data.get("workflows", [])
        workflows_label.set_text(f"Workflows: {len(workflows)}")
        workflow_table.rows = [
            {
                "id": w.get("id"),
                "name": w.get("name"),
                "status": w.get("status"),
                "steps": w.get("steps"),
                "created_at": w.get("created_at"),
            }
            for w in workflows
        ]

    ui.button("Refresh workflows", on_click=load_workflows).props("flat")
