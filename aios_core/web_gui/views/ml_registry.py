"""ML Registry view."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get, post


async def _get_models() -> list[dict]:
    data = await get("/api/models")
    return data if isinstance(data, list) else data.get("models", [])


async def _cycle_model_stage(name: str, stage: str) -> dict:
    return await post(f"/api/models/{name}/stage", json={"stage": stage})


def render() -> None:
    ui.label("ML Registry").classes("text-h6")

    models_label = ui.label("Loading models...").classes("text-body1")
    message_label = ui.label("").classes("text-body1 text-negative")
    model_table = ui.table(
        columns=[
            {"name": "name", "label": "Name", "field": "name"},
            {"name": "version", "label": "Version", "field": "version"},
            {"name": "framework", "label": "Framework", "field": "framework"},
            {"name": "stage", "label": "Stage", "field": "stage"},
            {"name": "size_mb", "label": "Size MB", "field": "size_mb"},
        ],
        rows=[],
    ).classes("w-full")

    async def load_models() -> None:
        models = await _get_models()
        models_label.set_text(f"Models: {len(models)}")
        model_table.rows = [
            {
                "name": m.get("name"),
                "version": m.get("version"),
                "framework": m.get("framework"),
                "stage": m.get("stage"),
                "size_mb": m.get("size_mb"),
            }
            for m in models
        ]

    async def cycle_stage(name: str) -> None:
        models = await _get_models()
        model = next((m for m in models if m.get("name") == name), None)
        if not model:
            return
        current = model.get("stage", "staging")
        next_stage = "production" if current == "staging" else "archived" if current == "production" else "staging"
        await _cycle_model_stage(name, next_stage)
        message_label.set_text(f"{name} moved to {next_stage}")
        await load_models()

    ui.button("Refresh models", on_click=load_models).props("flat")

    model_table.on("rowClick", lambda e: cycle_stage(e.args.get("name")))
