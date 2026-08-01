from nicegui import ui


def render_mobile_pwa_view():
    ui.add_head_html('<link rel="manifest" href="/static/manifest.json">')
    ui.add_head_html(
        '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">'
    )
    ui.add_head_html('<meta name="apple-mobile-web-app-capable" content="yes">')
    ui.add_head_html('<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">')

    ui.label("AIOS Mobile").classes("text-h5 q-mb-md text-center")

    with ui.column().classes("w-full gap-4 q-pa-md"):
        with ui.card().classes("w-full"):
            ui.label("Pending Approvals").classes("text-h6")
            ui.badge("3", color="negative").classes("absolute-top-right")
            ui.label("OLX: Discount request").classes("text-caption")
            ui.separator()
            with ui.row().classes("w-full justify-between"):
                ui.button("Reject", color="negative").classes("w-1/2")
                ui.button("Approve", color="positive").classes("w-1/2")

        with ui.card().classes("w-full"):
            ui.label("Active Negotiations").classes("text-h6")
            ui.label("Session #492: Counter-offer sent").classes("text-caption")
            ui.linear_progress(0.7).classes("w-full q-mt-sm")

        with ui.card().classes("w-full"):
            ui.label("System Health").classes("text-h6")
            with ui.row().classes("w-full justify-between"):
                ui.label("API").classes("text-positive")
                ui.label("99.9%").classes("text-grey")
