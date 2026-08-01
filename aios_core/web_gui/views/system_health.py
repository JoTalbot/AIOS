"""Operational health dashboard view."""
from nicegui import ui
from ..api_client import get

def render() -> None:
    ui.label("System Health").classes("text-h6")
    summary = ui.label("Loading health…").classes("text-body1")
    table = ui.table(columns=[{"name":"name","label":"Service","field":"name"},{"name":"status","label":"Status","field":"status"}], rows=[]).classes("w-full")
    ui.label("Alert History").classes("text-h6")
    alerts = ui.table(columns=[{"name":"timestamp","label":"Time","field":"timestamp"},{"name":"status","label":"Event","field":"status"},{"name":"failed","label":"Services","field":"failed"}], rows=[]).classes("w-full")
    async def refresh() -> None:
        try:
            data = await get("/api/system-health")
            summary.set_text(f"CPU: {data.get('cpu_percent')}% | Memory: {data.get('memory_percent')}% | Disk: {data.get('disk_percent')}%")
            table.rows = data.get("services", [])
            history = await get("/api/alert-history")
            alerts.rows = [{"timestamp": event.get("timestamp"), "status": event.get("status"), "failed": ", ".join(event.get("failed", [])) or "—"} for event in reversed(history.get("events", []))]
        except Exception as exc:
            summary.set_text(f"Health error: {exc}")
    ui.button("Refresh health", on_click=refresh).props("flat")
