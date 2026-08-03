"""Autonomy Escalate — уведомление владельца и персистентные подтверждения.

Когда guardrails возвращает MANUAL / ESCALATE, здесь формируется уведомление
владельцу в Telegram с коротким описанием и идентификатором approval.
Pending-запросы сохраняются в ``data/autonomy_approvals.json``.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from typing import Any

from . import _env

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
APPROVALS_PATH = PROJECT_ROOT / "data" / "autonomy_approvals.json"

_ALLOWED_VERDICTS = ("MANUAL", "ESCALATE")


def _load_approvals() -> list[dict]:
    try:
        return json.loads(APPROVALS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_approvals(items: list[dict]) -> None:
    APPROVALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    APPROVALS_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def create_approval(proposal: dict, decision) -> dict:
    """Создать запись на подтверждение. Возвращает {id, ...}."""
    items = _load_approvals()
    aid = f"ap_{int(time.time() * 1000)}"
    rec = {
        "id": aid,
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "verdict": decision.verdict,
        "reason": decision.reason,
        "proposal": proposal,
        "status": "pending",
    }
    items.append(rec)
    # храним максимум 200
    _save_approvals(items[-200:])
    return rec


def notify_owner(proposal: dict, decision, journal=None) -> dict:
    """Уведомить владельца в Telegram и сохранить approval."""
    rec = create_approval(proposal, decision)
    if journal:
        journal.log(platform=proposal.get("platform"), chat=proposal.get("chat"),
                    intent=proposal.get("intent"), action=proposal.get("action"),
                    params=proposal.get("params"), decision=decision.verdict,
                    reason=decision.reason, approval_id=rec["id"], result="escalated")
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat_id = _env("TELEGRAM_CHAT_ID")
    action = proposal.get("action", "?")
    text = (
        f"⚠️ <b>Автономия: требуется решение</b>\n"
        f"ID: <code>{rec['id']}</code>\n"
        f"Действие: <b>{action}</b> [{decision.verdict}]\n"
        f"Платформа: {proposal.get('platform')} · чат: {proposal.get('chat')}\n"
        f"Параметры: <code>{json.dumps(proposal.get('params', {}), ensure_ascii=False)[:300]}</code>\n"
        f"Причина: {decision.reason}\n"
        f"Команды: «подтверди {rec['id']}» / «отклони {rec['id']}»"
    )
    sent = False
    if token and chat_id:
        try:
            payload = {"chat_id": int(chat_id), "text": text[:3800],
                       "parse_mode": "HTML", "disable_web_page_preview": True}
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60):
                pass
            sent = True
        except Exception:
            pass
    rec["notified"] = sent
    return rec


def resolve(approval_id: str, approve: bool, journal=None) -> dict:
    """Подтвердить/отклонить approval. Возвращает {ok, action, params}."""
    items = _load_approvals()
    for rec in items:
        if rec.get("id") == approval_id:
            rec["status"] = "approved" if approve else "rejected"
            rec["resolved_ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _save_approvals(items)
            if journal:
                journal.log(action=rec["proposal"].get("action"),
                            decision="MANUAL_APPROVED" if approve else "REJECTED",
                            approval_id=approval_id, result="resolved")
            return {"ok": True, "approve": approve, "action": rec["proposal"].get("action"),
                    "params": rec["proposal"].get("params", {}),
                    "platform": rec["proposal"].get("platform"),
                    "chat": rec["proposal"].get("chat")}
    return {"ok": False, "error": "approval не найден"}
