"""Read-only bank app availability and notification metadata monitor."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .android_gateway import AndroidGateway


BANKS = {
    "abank": {"title": "A-Bank", "package": "ua.com.abank"},
    "privat24": {"title": "Privat24", "package": "ua.privatbank.ap24"},
}


def _read(path: Path, default):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, type(default)) else default
    except Exception:
        return default


class AndroidBankMonitor:
    """Return only app availability and event counts — never balances or text."""

    def __init__(self, root: Path | str, gateway_factory: Callable[[Path], AndroidGateway] = AndroidGateway):
        self.root = Path(root)
        self.gateway_factory = gateway_factory
        self.notifications_path = self.root / "data" / "android_gateway" / "notifications.json"

    def snapshot(self) -> dict:
        gateway = self.gateway_factory(self.root)
        profiles = {str(item.get("id")): item for item in (gateway.app_profiles().get("profiles") or [])}
        events = _read(self.notifications_path, [])
        rows = []
        for key, bank in BANKS.items():
            profile = profiles.get(key) or {}
            package = bank["package"]
            unread = sum(1 for event in events if isinstance(event, dict) and event.get("package") == package and not event.get("read"))
            rows.append({
                "id": key,
                "title": bank["title"],
                "available": bool(profile.get("available")),
                "unread_notifications": unread,
                "mode": "только уведомления и подтверждаемое открытие",
            })
        return {"status": "ok", "banks": rows}


def format_telegram(snapshot: dict) -> str:
    lines = ["🏦 <b>БАНКИ НА ТЕЛЕФОНЕ · БЕЗОПАСНЫЙ РЕЖИМ</b>", "━━━━━━━━━━━━━━━━"]
    for bank in snapshot.get("banks") or []:
        state = "✅ доступно" if bank.get("available") else "➕ не установлено"
        lines.append(f"• <b>{bank.get('title')}</b>: {state} · уведомлений: {bank.get('unread_notifications', 0)}")
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append("<i>Баланс, карты, OTP, переводы, платежи и биометрия не читаются и не выполняются.</i>")
    return "\n".join(lines)
