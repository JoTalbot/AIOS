"""Safety monitor view."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get


async def _get_safety() -> dict:
    return await get("/api/safety")


def render() -> None:
    ui.label("Safety").classes("text-h6")

    score_label = ui.label("Loading safety score...").classes("text-body1")
    status_chip = ui.chip("Loading...").props("outline")
    metrics_label = ui.label("Metrics: loading...").classes("text-body1")
    incidents_label = ui.label("Incidents: loading...").classes("text-body1")

    async def load_safety() -> None:
        data = await _get_safety()
        score = data.get("safety_score")
        status = data.get("status")
        metrics = data.get("metrics", {})
        incidents = data.get("recent_incidents", [])

        score_label.set_text(f"Safety score: {score}")
        status_chip.set_text(str(status))
        status_chip.props(f"color={'positive' if status == 'healthy' else 'warning'}")
        metrics_label.set_text(
            "Metrics: "
            f"harm={metrics.get('harm_score')} | "
            f"bias={metrics.get('bias_score')} | "
            f"deception={metrics.get('deception_score')} | "
            f"policy_rejections={metrics.get('policy_rejections')}"
        )
        incidents_label.set_text(f"Recent incidents: {len(incidents)}")

    ui.button("Refresh safety", on_click=load_safety).props("flat")
