"""Single metadata-only health snapshot for the real Android integration."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Callable

from .android_audit import PhoneActionAudit
from .android_bank_monitor import AndroidBankMonitor
from .android_gateway import AndroidGateway
from .android_leads import AndroidLeadQueue


TIMERS = (
    "aios-android-notifications.timer",
    "aios-android-leads.timer",
    "aios-ops-health.timer",
)


def _read_json(path: Path, default):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, type(default)) else default
    except Exception:
        return default


def _service_active(name: str) -> bool:
    return subprocess.run(["systemctl", "is-active", "--quiet", name], check=False).returncode == 0


class PhoneControlCenter:
    """Aggregate device, app, lead and workflow status without screen data."""

    def __init__(
        self,
        root: Path | str,
        gateway_factory: Callable[[Path], AndroidGateway] = AndroidGateway,
        service_probe: Callable[[str], bool] = _service_active,
        bank_monitor_factory: Callable[[Path], AndroidBankMonitor] = AndroidBankMonitor,
    ):
        self.root = Path(root)
        self.gateway_factory = gateway_factory
        self.service_probe = service_probe
        self.bank_monitor_factory = bank_monitor_factory

    def snapshot(self) -> dict:
        gateway = self.gateway_factory(self.root)
        device = gateway.status()
        capture = gateway.capture_status() if device.get("connected") else {}
        location = gateway.location_status() if device.get("connected") else {}
        profile_result = gateway.app_profiles() if device.get("connected") else {"profiles": []}
        profiles = profile_result.get("profiles") or []
        calibration = _read_json(self.root / "data" / "android_gateway" / "app_ui_calibrations.json", {})
        recovery = _read_json(self.root / "data" / "android_gateway" / "recovery.json", {})
        app_rows = []
        for profile in profiles:
            profile_id = str(profile.get("id") or "")
            cal = calibration.get(profile_id) if isinstance(calibration, dict) else {}
            app_rows.append({
                "id": profile_id,
                "title": str(profile.get("title") or profile_id),
                "available": bool(profile.get("available")),
                "calibrated": bool(isinstance(cal, dict) and cal.get("package")),
                "selectors": dict(cal.get("selectors") or {}) if isinstance(cal, dict) else {},
            })
        leads = AndroidLeadQueue(self.root).summary()
        audit = PhoneActionAudit(self.root).summary()
        banks = self.bank_monitor_factory(self.root).snapshot().get("banks") or []
        timers = {name: bool(self.service_probe(name)) for name in TIMERS}
        companion = device.get("companion") or {}
        connected = bool(device.get("connected"))
        companion_connected = bool(companion.get("connected"))
        issues = []
        if not connected:
            issues.append("adb_offline")
        if not companion_connected:
            issues.append("companion_offline")
        for name, active in timers.items():
            if not active:
                issues.append(f"timer:{name}")
        return {
            "status": "ok" if not issues else "degraded",
            "issues": issues,
            "device": {
                "connected": connected,
                "companion": companion_connected,
                "model": str(device.get("model") or ""),
                "android": str(device.get("android") or ""),
                "location_permission": bool(location.get("permission")),
                "location_ready": bool(location.get("ready")),
                "camera_permission": bool(capture.get("camera_permission")),
                "microphone_permission": bool(capture.get("microphone_permission")),
                "background_capture": bool(capture.get("background_capture")),
            },
            "apps": app_rows,
            "leads": {
                "pending": int(leads.get("pending") or 0),
                "crm_open": int(leads.get("crm_open") or 0),
                "crm_attention": int(leads.get("crm_attention") or 0),
                "crm_overdue": int(leads.get("crm_overdue") or 0),
            },
            "audit": {
                "count": int(audit.get("count") or 0),
                "last_action": str((audit.get("last") or {}).get("action") or ""),
                "last_status": str((audit.get("last") or {}).get("status") or ""),
            },
            "banks": [
                {"title": str(bank.get("title") or "Банк"), "available": bool(bank.get("available")), "unread_notifications": int(bank.get("unread_notifications") or 0)}
                for bank in banks
            ],
            "timers": timers,
            "recovery": {
                "status": str(recovery.get("status") or "unknown"),
                "action": str(recovery.get("action") or "unknown"),
            },
        }


def format_telegram(snapshot: dict) -> str:
    """Format a compact operator view without PII or screen content."""
    device = snapshot.get("device") or {}
    leads = snapshot.get("leads") or {}
    apps = snapshot.get("apps") or []
    timers = snapshot.get("timers") or {}
    banks = snapshot.get("banks") or []
    available = sum(1 for app in apps if app.get("available"))
    calibrated = sum(1 for app in apps if app.get("calibrated"))
    timers_ok = sum(1 for active in timers.values() if active)
    state = "✅ стабильно" if snapshot.get("status") == "ok" else "⚠️ требуется внимание"
    lines = [
        "📱 <b>ЦЕНТР УПРАВЛЕНИЯ ТЕЛЕФОНОМ</b>",
        f"Состояние: <b>{state}</b>",
        f"ADB: {'✅ подключён' if device.get('connected') else '⚠️ офлайн'} · Companion: {'✅ активен' if device.get('companion') else '⚠️ недоступен'}",
        f"Геолокация: {'✅ готова' if device.get('location_ready') else ('🟡 разрешена, но системно недоступна' if device.get('location_permission') else '⚠️ не разрешена')}",
        f"Камера: {'✅ разрешена' if device.get('camera_permission') else '⚪ не разрешена'} · микрофон: {'✅ разрешён' if device.get('microphone_permission') else '⚪ не разрешён'} · фоновой захват: {'⚠️' if device.get('background_capture') else 'выключен'}",
        f"Приложения: {available}/{len(apps)} доступны · интерфейсы откалиброваны: {calibrated}",
        f"Лиды: {leads.get('pending', 0)} · CRM follow-up: {leads.get('crm_open', 0)} · внимание: {leads.get('crm_attention', 0)} · просрочены: {leads.get('crm_overdue', 0)}",
        "Банки: " + (" · ".join(f"{bank.get('title')}: {bank.get('unread_notifications', 0)} уведомл." for bank in banks) if banks else "нет данных"),
        f"Таймеры: {timers_ok}/{len(timers)} активны · аудит: {snapshot.get('audit', {}).get('count', 0)} событий",
        f"Восстановление: {snapshot.get('recovery', {}).get('action', 'unknown')}",
    ]
    if snapshot.get("issues"):
        lines.append("Проблемы: <code>" + ", ".join(str(value) for value in snapshot["issues"]) + "</code>")
    return "\n".join(lines)
