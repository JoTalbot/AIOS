"""Admin panel view with detailed backup management."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get, post


async def _get_backups() -> dict:
    return await get("/api/backups")


async def _create_backup(label: str = "dashboard") -> dict:
    return await post("/api/backups", json={"action": "create", "label": label})


async def _verify_backup(backup_id: str) -> dict:
    return await post("/api/backups", json={"action": "verify", "backup_id": backup_id})


async def _test_restore(backup_id: str) -> dict:
    return await post("/api/backups", json={"action": "test_restore", "backup_id": backup_id})


def render() -> None:
    ui.label("Admin").classes("text-h6")

    status_label = ui.label("").classes("text-body1")

    backup_table = ui.table(
        columns=[
            {"name": "id", "label": "ID", "field": "id"},
            {"name": "label", "label": "Label", "field": "label"},
            {"name": "size_mb", "label": "Size MB", "field": "size_mb"},
            {"name": "verified", "label": "Verified", "field": "verified"},
            {"name": "created_at", "label": "Created", "field": "created_at"},
        ],
        rows=[],
    ).classes("w-full")

    async def load_backups() -> None:
        data = await _get_backups()
        backups = data.get("backups", [])
        status_label.set_text(f"Backups: {len(backups)}")
        backup_table.rows = [
            {
                "id": b.get("id"),
                "label": b.get("label"),
                "size_mb": b.get("size_mb"),
                "verified": "✓" if b.get("verified") else "✗",
                "created_at": b.get("created_at"),
            }
            for b in backups
        ]

    async def do_create_backup() -> None:
        res = await _create_backup(label="dashboard")
        ui.notify(res)
        await load_backups()

    async def do_verify_backup(backup_id: str) -> None:
        res = await _verify_backup(backup_id)
        ui.notify(res)
        await load_backups()

    async def do_test_restore() -> None:
        if not backup_table.rows:
            ui.notify("No backup available", type="warning")
            return
        backup_id = backup_table.rows[0].get("id")
        res = await _test_restore(backup_id)
        ui.notify("Restore test passed" if res.get("ok") else str(res), type="positive" if res.get("ok") else "negative")

    with ui.row():
        ui.button("Refresh backups", on_click=load_backups).props("flat")
        ui.button("Create backup", on_click=do_create_backup).props("color=positive")
        ui.button("Test latest restore", on_click=do_test_restore).props("flat")

    backup_table.on("rowClick", lambda e: do_verify_backup(e.args.get("id")))
