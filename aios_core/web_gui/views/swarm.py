"""Swarm view."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get


async def _get_agents() -> dict:
    return await get("/api/agents")


def render() -> None:
    ui.label("Swarm").classes("text-h6")

    agents_label = ui.label("Loading agents...").classes("text-body1")
    agent_table = ui.table(
        columns=[
            {"name": "agent_id", "label": "ID", "field": "agent_id"},
            {"name": "name", "label": "Name", "field": "name"},
            {"name": "role", "label": "Role", "field": "role"},
            {"name": "status", "label": "Status", "field": "status"},
            {"name": "autonomy_level", "label": "Autonomy", "field": "autonomy_level"},
            {"name": "completed_tasks", "label": "Tasks", "field": "completed_tasks"},
        ],
        rows=[],
    ).classes("w-full")

    async def load_agents() -> None:
        data = await _get_agents()
        agents = data if isinstance(data, list) else data.get("agents", [])
        agents_label.set_text(f"Agents: {len(agents)}")
        agent_table.rows = [
            {
                "agent_id": a.get("agent_id"),
                "name": a.get("name"),
                "role": a.get("role"),
                "status": a.get("status"),
                "autonomy_level": a.get("autonomy_level"),
                "completed_tasks": a.get("completed_tasks"),
            }
            for a in agents
        ]

    ui.button("Refresh swarm", on_click=load_agents).props("flat")
