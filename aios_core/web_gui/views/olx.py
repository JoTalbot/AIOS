"""OLX integration view."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get


async def _get_olx_queries() -> dict:
    return await get("/api/olx/queries")


async def _get_olx_analytics() -> dict:
    return await get("/api/olx/analytics")


def render() -> None:
    ui.label("OLX").classes("text-h6")

    queries_label = ui.label("Queries: loading...").classes("text-body1")
    analytics_label = ui.label("Analytics: loading...").classes("text-body1")

    async def load_queries() -> None:
        data = await _get_olx_queries()
        queries = data.get("queries", [])
        queries_label.set_text(f"Queries: {len(queries)}")
        table.rows = [
            {
                "query": q.get("query"),
                "status": q.get("status"),
                "last_run": q.get("last_run"),
            }
            for q in queries
        ]

    async def load_analytics() -> None:
        data = await _get_olx_analytics()
        analytics_label.set_text(
            f"Total: {data.get('total', 'N/A')} | "
            f"Success: {data.get('success', 'N/A')} | "
            f"Failed: {data.get('failed', 'N/A')}"
        )

    ui.button("Refresh queries", on_click=load_queries).props("flat")
    ui.button("Refresh analytics", on_click=load_analytics).props("flat")

    columns = [
        {"name": "query", "label": "Query", "field": "query"},
        {"name": "status", "label": "Status", "field": "status"},
        {"name": "last_run", "label": "Last Run", "field": "last_run"},
    ]
    table = ui.table(columns=columns, rows=[]).classes("w-full")
