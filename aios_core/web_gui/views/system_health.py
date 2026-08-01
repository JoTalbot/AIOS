"""Operational health dashboard view."""
from nicegui import ui
from ..api_client import get

def render() -> None:
    ui.label("System Health").classes("text-h6")
    summary = ui.label("Loading health…").classes("text-body1")
    table = ui.table(columns=[{"name":"name","label":"Service","field":"name"},{"name":"status","label":"Status","field":"status"}], rows=[]).classes("w-full")
    async def refresh() -> None:
        try:
            data = await get("/api/system-health")
            summary.set_text(f"CPU: {data.get('cpu_percent')}% | Memory: {data.get('memory_percent')}% | Disk: {data.get('disk_percent')}%")
            table.rows = data.get("services", [])
        except Exception as exc:
            summary.set_text(f"Health error: {exc}")
    ui.button("Refresh health", on_click=refresh).props("flat")
