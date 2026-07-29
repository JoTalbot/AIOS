"""Webhook Router — endpoints для получения входящих сообщений от платформ."""
from __future__ import annotations
import os
import hmac
import hashlib
from typing import Dict, Any
from starlette.routing import Router, Route
from starlette.requests import Request
from starlette.responses import JSONResponse
from datetime import datetime


# === Безопасность: проверка подписи ===
def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Проверить HMAC-SHA256 подпись webhook."""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

# === Instagram Webhook (Meta) ===
async def instagram_verify(request: Request):
    """Instagram verification challenge (GET)."""
    params = request.query_params
    if params.get("hub.verify_token") == os.getenv("INSTAGRAM_VERIFY_TOKEN"):
        return JSONResponse({"challenge": params.get("hub.challenge")})
    return JSONResponse({"error": "Invalid token"}, status_code=403)

async def instagram_webhook(request: Request):
    """Instagram incoming messages (POST)."""
    body = await request.body()
    # TODO: Проверка подписи X-Hub-Signature-256
    data = await request.json()
    
    # Парсинг Instagram webhook payload
    messages = []
    for entry in data.get("entry", []):
        for messaging in entry.get("messaging", []):
            if "message" in messaging:
                messages.append({
                    "platform": "instagram",
                    "sender_id": messaging["sender"]["id"],
                    "text": messaging["message"].get("text", ""),
                    "message_id": messaging["message"]["mid"],
                    "timestamp": datetime.fromtimestamp(messaging["timestamp"])
                })
    
    # TODO: Передать в AIAdvisor pipeline
    # for msg in messages:
    #     await advisor.process_and_respond(...)
    
    return JSONResponse({"status": "ok", "processed": len(messages)})

# === OLX Webhook ===
async def olx_webhook(request: Request):
    """OLX incoming messages."""
    body = await request.body()
    signature = request.headers.get("X-OLX-Signature", "")
    secret = os.getenv("OLX_WEBHOOK_SECRET", "")
    
    if secret and not verify_signature(body, signature, secret):
        return JSONResponse({"error": "Invalid signature"}, status_code=401)
    
    data = await request.json()
    # TODO: Парсинг OLX payload и передача в AIAdvisor
    
    return JSONResponse({"status": "ok"})

# === Viber Webhook ===
async def viber_webhook(request: Request):
    """Viber incoming messages."""
    data = await request.json()
    if data.get("event") == "message":
        message = {
            "platform": "viber",
            "sender_id": data["sender"]["id"],
            "sender_name": data["sender"]["name"],
            "text": data["message"].get("text", ""),
            "message_id": data["message_token"]
        }
        # TODO: Передать в AIAdvisor
    return JSONResponse({"status": "ok"})

# === WhatsApp (Meta Cloud API) ===
async def whatsapp_verify(request: Request):
    """WhatsApp verification challenge."""
    params = request.query_params
    if params.get("hub.verify_token") == os.getenv("WHATSAPP_VERIFY_TOKEN"):
        return JSONResponse(content=params.get("hub.challenge"))
    return JSONResponse({"error": "Invalid token"}, status_code=403)

async def whatsapp_webhook(request: Request):
    """WhatsApp incoming messages."""
    data = await request.json()
    messages = []
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                if msg.get("type") == "text":
                    messages.append({
                        "platform": "whatsapp",
                        "sender_id": msg["from"],
                        "text": msg["text"]["body"],
                        "message_id": msg["id"]
                    })
    return JSONResponse({"status": "ok", "processed": len(messages)})

# === Facebook Messenger ===
async def facebook_verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == os.getenv("FACEBOOK_VERIFY_TOKEN"):
        return JSONResponse(content=params.get("hub.challenge"))
    return JSONResponse({"error": "Invalid token"}, status_code=403)

async def facebook_webhook(request: Request):
    """Facebook Messenger incoming messages."""
    data = await request.json()
    messages = []
    for entry in data.get("entry", []):
        for messaging in entry.get("messaging", []):
            if "message" in messaging:
                messages.append({
                    "platform": "facebook",
                    "sender_id": messaging["sender"]["id"],
                    "text": messaging["message"].get("text", ""),
                    "message_id": messaging["message"]["mid"]
                })
    return JSONResponse({"status": "ok", "processed": len(messages)})


# Starlette Router не поддерживает декораторы — регистрируем маршруты явно.
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
