"""No-action readiness report for phone workflows."""
from __future__ import annotations

import json
from pathlib import Path


REQUIREMENTS = {
    "whatsapp": {"title": "WhatsApp", "selectors": ("chat_search",)},
    "ime": {"title": "iMe Messenger", "selectors": ("chat_search",)},
    "uklon": {"title": "Uklon Passenger", "selectors": ("pickup_address", "destination_address")},
    "easyway": {"title": "EasyWay", "selectors": ("destination_trigger",)},
}


def _read(path: Path, default):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, type(default)) else default
    except Exception:
        return default


class PhoneWorkflowReadiness:
    """Assess stored calibration metadata only; it never opens apps or chats."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.calibration_path = self.root / "data" / "android_gateway" / "app_ui_calibrations.json"

    def snapshot(self) -> dict:
        calibrations = _read(self.calibration_path, {})
        rows = []
        for profile, config in REQUIREMENTS.items():
            cal = calibrations.get(profile) if isinstance(calibrations, dict) else {}
            selectors = dict(cal.get("selectors") or {}) if isinstance(cal, dict) else {}
            required = config["selectors"]
            ready = bool(cal) and all(bool(selectors.get(selector)) for selector in required)
            rows.append({
                "id": profile,
                "title": config["title"],
                "ready": ready,
                "required": len(required),
                "available": sum(bool(selectors.get(selector)) for selector in required),
            })
        return {"status": "ok", "workflows": rows, "ready": sum(1 for row in rows if row["ready"]), "total": len(rows)}


def format_telegram(snapshot: dict) -> str:
    lines = ["🧪 <b>ПРОВЕРКА СЦЕНАРИЕВ ТЕЛЕФОНА</b>", "━━━━━━━━━━━━━━━━"]
    for row in snapshot.get("workflows") or []:
        state = "✅ готов" if row.get("ready") else "🟡 нужна калибровка"
        lines.append(f"• <b>{row.get('title')}</b>: {state} · элементы: {row.get('available', 0)}/{row.get('required', 0)}")
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append("<i>Проверка не открывает чат, не вводит текст, не выбирает адрес и не выполняет внешних действий.</i>")
    return "\n".join(lines)
