"""ML Registry view."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get


async def _get_models() -> list[dict]:
    data = await get("/api/models")
    return data if isinstance(data, list) else data.get("models", [])


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


    ui.button("Refresh models", on_click=load_models).props("flat")

    ui.label("Реестр моделей доступен только для просмотра: изменение этапа требует подключённого Model Registry.").classes("text-caption text-warning")
