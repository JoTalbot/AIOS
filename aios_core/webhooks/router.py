"""Webhook Router — endpoints for receiving incoming messages from platforms."""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timezone
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, Router


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify HMAC-SHA256 signature of webhook payload.

    Args:
        payload: Raw request body bytes.
        signature: Signature from the webhook header.
        secret: Shared secret key.

    Returns:
        True if signature is valid, False otherwise.
    """
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def instagram_verify(request: Request) -> Response:
    """
    Instagram verification challenge (GET).

    Protect against CSRF by verifying token from environment variable.

    Args:
        request: Incoming HTTP request.

    Returns:
        JSONResponse with challenge or error.
    """
    params = request.query_params
    verify_token = params.get("hub.verify_token")
    expected_token = os.getenv("INSTAGRAM_VERIFY_TOKEN")
    if verify_token and expected_token and verify_token == expected_token:
        challenge = params.get("hub.challenge")
        # Return plain text challenge per Instagram spec, wrapped in JSONResponse for consistency
        return JSONResponse({"challenge": challenge})
    return JSONResponse({"error": "Invalid token"}, status_code=403)


async def instagram_webhook(request: Request) -> Response:
    """
    Instagram incoming messages (POST).

    Verifies X-Hub-Signature-256 header to prevent XSS/CSRF attacks.

    Args:
        request: Incoming HTTP request.

    Returns:
        JSONResponse with processing status.
    """
    secret = os.getenv("INSTAGRAM_APP_SECRET")
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()

    if secret:
        # Signature header format: "sha256=..."
        if not signature_header.startswith("sha256="):
            return JSONResponse({"error": "Invalid signature header"}, status_code=401)
        signature = signature_header.split("=", 1)[1]
        if not verify_signature(body, signature, secret):
            return JSONResponse({"error": "Invalid signature"}, status_code=401)

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    messages = [
        {
            "platform": "instagram",
            "sender_id": messaging["sender"]["id"],
            "text": messaging["message"].get("text", ""),
            "message_id": messaging["message"]["mid"],
            "timestamp": datetime.fromtimestamp(messaging["timestamp"], tz=timezone.utc),
        }
        for entry in data.get("entry", [])
        for messaging in entry.get("messaging", [])
        if "message" in messaging
    ]

    # TODO: Передать в AIAdvisor pipeline
    # for msg in messages:
    #     await advisor.process_and_respond(...)

    return JSONResponse({"status": "ok", "processed": len(messages)})


async def olx_webhook(request: Request) -> Response:
    """
    OLX incoming messages.

    Verifies X-OLX-Signature header to prevent unauthorized requests.

    Args:
        request: Incoming HTTP request.

    Returns:
        JSONResponse with processing status.
    """
    body = await request.body()
    signature = request.headers.get("X-OLX-Signature", "")
    secret = os.getenv("OLX_WEBHOOK_SECRET", "")

    if secret and not verify_signature(body, signature, secret):
        return JSONResponse({"error": "Invalid signature"}, status_code=401)

    try:
        await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    # TODO: Парсинг OLX payload и передача в AIAdvisor

    return JSONResponse({"status": "ok"})


async def viber_webhook(request: Request) -> Response:
    """
    Viber incoming messages.

    Args:
        request: Incoming HTTP request.

    Returns:
        JSONResponse with processing status.
    """
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    if data.get("event") == "message":
        # TODO: Передать в AIAdvisor карточку сообщения
        pass
    return JSONResponse({"status": "ok"})


async def whatsapp_verify(request: Request) -> Response:
    """
    WhatsApp verification challenge.

    Protect against CSRF by verifying token from environment variable.

    Args:
        request: Incoming HTTP request.

    Returns:
        JSONResponse with challenge or error.
    """
    params = request.query_params
    verify_token = params.get("hub.verify_token")
    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
    if verify_token and expected_token and verify_token == expected_token:
        challenge = params.get("hub.challenge")
        # WhatsApp expects plain text response, but JSONResponse is used for consistency
        return JSONResponse(content=challenge)
    return JSONResponse({"error": "Invalid token"}, status_code=403)


async def whatsapp_webhook(request: Request) -> Response:
    """
    WhatsApp incoming messages.

    Args:
        request: Incoming HTTP request.

    Returns:
        JSONResponse with processing status.
    """
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    messages = [
        {
            "platform": "whatsapp",
            "sender_id": msg["from"],
            "text": msg["text"]["body"],
            "message_id": msg["id"],
        }
        for entry in data.get("entry", [])
        for change in entry.get("changes", [])
        for msg in change.get("value", {}).get("messages", [])
        if msg.get("type") == "text"
    ]
    return JSONResponse({"status": "ok", "processed": len(messages)})


async def facebook_verify(request: Request) -> Response:
    """
    Facebook Messenger verification challenge.

    Protect against CSRF by verifying token from environment variable.

    Args:
        request: Incoming HTTP request.

    Returns:
        JSONResponse with challenge or error.
    """
    params = request.query_params
    verify_token = params.get("hub.verify_token")
    expected_token = os.getenv("FACEBOOK_VERIFY_TOKEN")
    if verify_token and expected_token and verify_token == expected_token:
        challenge = params.get("hub.challenge")
        # Facebook expects plain text response, but JSONResponse is used for consistency
        return JSONResponse(content=challenge)
    return JSONResponse({"error": "Invalid token"}, status_code=403)


async def facebook_webhook(request: Request) -> Response:
    """
    Facebook Messenger incoming messages.

    Args:
        request: Incoming HTTP request.

    Returns:
        JSONResponse with processing status.
    """
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    messages = [
        {
            "platform": "facebook",
            "sender_id": messaging["sender"]["id"],
            "text": messaging["message"].get("text", ""),
            "message_id": messaging["message"]["mid"],
        }
        for entry in data.get("entry", [])
        for messaging in entry.get("messaging", [])
        if "message" in messaging
    ]
    return JSONResponse({"status": "ok", "processed": len(messages)})


router = Router(
    routes=[
        Route("/webhooks/instagram", instagram_verify, methods=["GET"]),
        Route("/webhooks/instagram", instagram_webhook, methods=["POST"]),
        Route("/webhooks/olx", olx_webhook, methods=["POST"]),
        Route("/webhooks/viber", viber_webhook, methods=["POST"]),
        Route("/webhooks/whatsapp", whatsapp_verify, methods=["GET"]),
        Route("/webhooks/whatsapp", whatsapp_webhook, methods=["POST"]),
        Route("/webhooks/facebook", facebook_verify, methods=["GET"]),
        Route("/webhooks/facebook", facebook_webhook, methods=["POST"]),
    ]
)