"""Overview view with detailed stats and live metrics."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get


def render() -> None:
    ui.label("Overview").classes("text-h6")

    stats_label = ui.label("Loading stats...").classes("text-body1")

    with ui.row().classes("w-full gap-4"):
        cpu_card = ui.card().classes("flex-1 p-4")
        with cpu_card:
            ui.label("CPU").classes("text-caption text-gray-500")
            cpu_value = ui.label("--").classes("text-h4 font-bold")

        mem_card = ui.card().classes("flex-1 p-4")
        with mem_card:
            ui.label("Memory").classes("text-caption text-gray-500")
            mem_value = ui.label("--").classes("text-h4 font-bold")

        disk_card = ui.card().classes("flex-1 p-4")
        with disk_card:
            ui.label("Disk").classes("text-caption text-gray-500")
            disk_value = ui.label("--").classes("text-h4 font-bold")

    async def load_stats() -> None:
        try:
            data = await get("/api/stats")
            cpu = data.get("cpu", "N/A")
            memory = data.get("memory", "N/A")
            disk = data.get("disk", "N/A")
            stats_label.set_text(f"CPU: {cpu} | Memory: {memory} | Disk: {disk}")
            cpu_value.set_text(str(cpu))
            mem_value.set_text(str(memory))
            disk_value.set_text(str(disk))
        except Exception as e:
            stats_label.set_text(f"Error loading stats: {e}")

    ui.button("Refresh stats", on_click=load_stats).props("flat")
