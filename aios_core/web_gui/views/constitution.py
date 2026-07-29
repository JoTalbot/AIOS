"""Constitution view."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get


async def _get_constitution() -> dict:
    return await get("/api/constitution")


async def _get_constitution_article(number: int) -> dict:
    return await get(f"/api/constitution/{number}")


def render() -> None:
    ui.label("Constitution").classes("text-h6")

    article_table = ui.table(
        columns=[
            {"name": "number", "label": "#", "field": "number"},
            {"name": "title", "label": "Title", "field": "title"},
            {"name": "status", "label": "Status", "field": "status"},
            {"name": "level", "label": "Level", "field": "level"},
            {"name": "scope", "label": "Scope", "field": "scope"},
        ],
        rows=[],
    ).classes("w-full")

    article_dialog = ui.dialog()
    with article_dialog, ui.card().classes("w-full max-w-3xl"):
        ui.label("Article").classes("text-h6")
        article_content = ui.markdown("").classes("w-full")

    async def load_constitution() -> None:
        data = await _get_constitution()
        articles = data if isinstance(data, list) else data.get("articles", [])
        article_table.rows = [
            {
                "number": a.get("number"),
                "title": a.get("title"),
                "status": a.get("status"),
                "level": a.get("level"),
                "scope": a.get("scope"),
            }
            for a in articles
        ]

    async def open_article(e) -> None:
        row = e.args.get("row", {})
        number = row.get("number")
        if not number:
            return
        data = await _get_constitution_article(number)
        body = data.get("body", "")
        article_content.set_content(body or "*No content*")
        article_dialog.open()

    article_table.on("rowClick", open_article)
    ui.button("Refresh constitution", on_click=load_constitution).props("flat")
