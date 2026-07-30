"""Main NiceGUI application for AIOS dashboard."""

from __future__ import annotations

import os
import sys

from nicegui import ui

from .api_client import (
    get_android_devices,
    get_auto_study_history,
    get_auto_study_status,
    start_auto_study,
)
from .views import (
    admin,
    audit,
    chat,
    constitution,
    fleet,
    knowledge,
    memories,
    ml_registry,
    olx,
    overview,
    platforms,
    processes,
    safety,
    services,
    swarm,
    workflows,
)

# Enable dark mode globally
ui.dark_mode().enable()


@ui.page("/")
def index() -> None:
    with ui.header().classes("items-center justify-between bg-primary text-white"):
        ui.label("AIOS Dashboard").classes("text-h5 font-bold")
        ui.link("API (FastAPI)", "http://127.0.0.1:8000/docs", new_tab=True).classes("text-white")

    with ui.tabs().classes("w-full bg-primary text-white") as tabs:
        ui.tab("Overview", icon="dashboard")
        ui.tab("Services", icon="settings")
        ui.tab("Auto-Study", icon="android")
        ui.tab("Devices", icon="smartphone")
        ui.tab("OLX", icon="shopping_cart")
        ui.tab("Fleet", icon="devices")
        ui.tab("Platforms", icon="widgets")
        ui.tab("Audit", icon="history")
        ui.tab("Safety", icon="shield")
        ui.tab("Admin", icon="admin_panel_settings")
        ui.tab("Chat", icon="chat")
        ui.tab("Constitution", icon="gavel")
        ui.tab("Knowledge Graph", icon="account_tree")
        ui.tab("ML Registry", icon="memory")
        ui.tab("Memories", icon="psychology")
        ui.tab("Processes", icon="settings_applications")
        ui.tab("Swarm", icon="group")
        ui.tab("Workflows", icon="account_tree")

    with ui.tab_panels(tabs, value="Overview").classes("w-full"):
        with ui.tab_panel("Overview"):
            overview.render()
        with ui.tab_panel("Services"):
            services.render()
        with ui.tab_panel("Auto-Study"):
            auto_study_page()
        with ui.tab_panel("Devices"):
            devices_page()
        with ui.tab_panel("OLX"):
            olx.render()
        with ui.tab_panel("Fleet"):
            fleet.render()
        with ui.tab_panel("Platforms"):
            platforms.render()
        with ui.tab_panel("Audit"):
            audit.render()
        with ui.tab_panel("Safety"):
            safety.render()
        with ui.tab_panel("Admin"):
            admin.render()
        with ui.tab_panel("Chat"):
            chat.render()
        with ui.tab_panel("Constitution"):
            constitution.render()
        with ui.tab_panel("Knowledge Graph"):
            knowledge.render()
        with ui.tab_panel("ML Registry"):
            ml_registry.render()
        with ui.tab_panel("Memories"):
            memories.render()
        with ui.tab_panel("Processes"):
            processes.render()
        with ui.tab_panel("Swarm"):
            swarm.render()
        with ui.tab_panel("Workflows"):
            workflows.render()


def auto_study_page() -> None:
    ui.label("Android Auto-Study").classes("text-h6")
    status = ui.label("Loading...").classes("text-body1")

    async def refresh_status() -> None:
        try:
            data = await get_auto_study_status()
            status.set_text(
                f"Active: {data.get('active')} | "
                f"Package: {data.get('package')} | "
                f"Scenario: {data.get('scenario')} | "
                f"Progress: {data.get('progress')}"
            )
        except Exception as e:
            status.set_text(f"Auto-study status: {e}")

    ui.button("Refresh status", on_click=refresh_status).props("flat")

    async def start_study() -> None:
        pkg = package_input.value or "ua.slando"
        scn = scenario_input.value or "basic_explore"
        try:
            res = await start_auto_study(package=pkg, scenario=scn)
            ui.notify(str(res))
        except Exception as e:
            ui.notify(f"Start study note: {e}")

    with ui.row():
        package_input = ui.input("Package", value="ua.slando").classes("w-40")
        scenario_input = ui.input("Scenario", value="basic_explore").classes("w-40")
    ui.button("Start study", on_click=start_study).props("color=positive")

    ui.separator()
    ui.label("History").classes("text-h6")

    async def load_history() -> None:
        try:
            data = await get_auto_study_history()
            history = data.get("history", [])
            table.rows = [
                {
                    "study_id": h.get("study_id"),
                    "package": h.get("package"),
                    "scenario": h.get("scenario"),
                    "status": h.get("status"),
                    "error": h.get("error"),
                }
                for h in history[:20]
            ]
        except Exception as e:
            ui.notify(f"History: {e}")

    columns = [
        {"name": "study_id", "label": "Study ID", "field": "study_id"},
        {"name": "package", "label": "Package", "field": "package"},
        {"name": "scenario", "label": "Scenario", "field": "scenario"},
        {"name": "status", "label": "Status", "field": "status"},
        {"name": "error", "label": "Error", "field": "error"},
    ]
    table = ui.table(columns=columns, rows=[]).classes("w-full")
    ui.button("Load history", on_click=load_history).props("flat")


def devices_page() -> None:
    ui.label("Android Devices").classes("text-h6")

    async def load_devices() -> None:
        try:
            data = await get_android_devices()
            devices = data.get("devices", [])
            table.rows = [{"device": str(d)} for d in devices]
        except Exception as e:
            ui.notify(f"Devices: {e}")

    columns = [{"name": "device", "label": "Device", "field": "device"}]
    table = ui.table(columns=columns, rows=[]).classes("w-full")
    ui.button("Refresh devices", on_click=load_devices).props("flat")


def run() -> None:
    try:
        from aios_core.advisor.templates_engine import TemplateEngine
        from aios_core.dashboard.views.advisor_templates_view import render_advisor_templates_view

        template_engine = TemplateEngine(storage_path="data/templates")

        @ui.page("/advisor/templates", title="AI Advisor — Шаблоны")
        def advisor_templates_page():
            render_advisor_templates_view(template_engine)
    except Exception as e:
        print(f"Advisor templates view note: {e}")

    try:
        from aios_core.advisor.metrics_collector import MetricsCollector
        from aios_core.dashboard.views.metrics_view import render_metrics_view

        metrics_collector = MetricsCollector(storage_path="data/metrics")

        @ui.page("/advisor/metrics", title="AI Advisor — Метрики")
        def advisor_metrics_page():
            render_metrics_view(metrics_collector)
    except Exception as e:
        print(f"Advisor metrics view note: {e}")

    dash_host = os.environ.get("AIOS_DASH_HOST", "0.0.0.0")
    dash_port = int(os.environ.get("AIOS_DASH_PORT", "8080"))
    print(f"🌐 Launching AIOS Pure-Python Dashboard on http://{dash_host}:{dash_port}")
    ui.run(title="AIOS Pure-Python Dashboard", favicon="🤖", host=dash_host, port=dash_port, reload=False)
