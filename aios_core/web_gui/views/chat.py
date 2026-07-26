"""Chat view."""

from __future__ import annotations

from nicegui import ui

from ..api_client import get, post


async def _get_chat() -> dict:
    return await get("/api/chat")


async def _send_chat(message: str) -> dict:
    return await post("/api/chat", json={"message": message})


def render() -> None:
    ui.label("Chat").classes("text-h6")

    status_label = ui.label("Loading...").classes("text-body1")
    message_label = ui.label("").classes("text-body1")
    input_field = ui.input("Message", value="").classes("w-full")
    sending = False

    async def refresh_status() -> None:
        data = await _get_chat()
        status_label.set_text(f"Status: {data.get('status')}")
        message_label.set_text(data.get("message", ""))

    async def send_message() -> None:
        nonlocal sending
        if sending:
            return
        sending = True
        message = input_field.value.strip()
        if not message:
            return
        res = await _send_chat(message)
        message_label.set_text(res.get("message", ""))
        input_field.value = ""
        sending = False

    ui.button("Refresh status", on_click=refresh_status).props("flat")
    ui.button("Send", on_click=send_message).props("color=positive")
