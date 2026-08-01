from nicegui import ui


def render_onboarding_view(flow):
    ui.label("Добро пожаловать в AIOS!").classes("text-h4 q-mb-md")
    progress = flow.get_progress("ws_default")

    ui.linear_progress(progress["percent"] / 100).classes("w-full q-mb-lg")
    ui.label(f"Прогресс: {progress['percent']}%").classes("text-caption text-grey q-mb-md")

    for step in flow.steps:
        with ui.card().classes("w-full q-mb-sm"), ui.row().classes("w-full items-center justify-between"):
            ui.label(step["title"]).classes("text-h6")
            if step["done"]:
                ui.icon("check_circle", color="positive", size="2em")
            else:
                ui.button("Выполнить", color="primary").classes("q-ml-md")
