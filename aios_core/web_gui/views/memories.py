"""Memories view."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get


async def _get_memories() -> dict:
    return await get("/api/memories")


def render() -> None:
    ui.label("Memories").classes("text-h6")

    memories_label = ui.label("Loading memories...").classes("text-body1")
    memory_table = ui.table(
        columns=[
            {"name": "id", "label": "ID", "field": "id"},
            {"name": "category", "label": "Category", "field": "category"},
            {"name": "source", "label": "Source", "field": "source"},
            {"name": "confidence", "label": "Confidence", "field": "confidence"},
            {"name": "created_at", "label": "Created", "field": "created_at"},
        ],
        rows=[],
    ).classes("w-full")

    async def load_memories() -> None:
        data = await _get_memories()
        items = data.get("items", [])
        memories_label.set_text(f"Memories: {len(items)}")
        memory_table.rows = [
            {
                "id": m.get("id"),
                "category": m.get("category"),
                "source": m.get("source"),
                "confidence": m.get("confidence"),
                "created_at": m.get("created_at"),
            }
            for m in items
        ]

    ui.button("Refresh memories", on_click=load_memories).props("flat")
