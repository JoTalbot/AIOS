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
from .followup_templates import FollowupTemplateStore
from .phone_state_health import PhoneStateHealth
from .phone_sync_status import PhoneSyncStatus
from .phone_inventory import PhoneInventory


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
        template_store_factory: Callable[[Path], FollowupTemplateStore] = FollowupTemplateStore,
        state_health_factory: Callable[[Path], PhoneStateHealth] = PhoneStateHealth,
        sync_status_factory: Callable[[Path], PhoneSyncStatus] = PhoneSyncStatus,
        inventory_factory: Callable[[Path], PhoneInventory] = PhoneInventory,
    ):
        self.root = Path(root)
        self.gateway_factory = gateway_factory
        self.service_probe = service_probe
        self.bank_monitor_factory = bank_monitor_factory
        self.template_store_factory = template_store_factory
        self.state_health_factory = state_health_factory
        self.sync_status_factory = sync_status_factory
        self.inventory_factory = inventory_factory

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
        templates = self.template_store_factory(self.root).summary()
        audit = PhoneActionAudit(self.root).summary()
        state_health = self.state_health_factory(self.root).snapshot()
        sync_status = self.sync_status_factory(self.root).snapshot()
        inventory = self.inventory_factory(self.root).latest()
        bank_snapshot = self.bank_monitor_factory(self.root).snapshot()
        banks = bank_snapshot.get("banks") or []
        bank_tasks = bank_snapshot.get("tasks") or {}
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
                "by_source": dict(leads.get("by_source") or {}),
            },
            "templates": {
                "count": int(templates.get("count") or 0),
                "stale": int(templates.get("stale") or 0),
                "used_total": int(templates.get("used_total") or 0),
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
            "bank_tasks": {
                "pending": int(bank_tasks.get("pending") or 0),
                "attention": int(bank_tasks.get("attention") or 0),
                "overdue": int(bank_tasks.get("overdue") or 0),
            },
            "sync": {"fresh": int(sync_status.get("fresh") or 0), "total": int(sync_status.get("total") or 0), "sources": sync_status.get("sources") or []},
            "inventory": {
                "android": str(inventory.get("android") or ""), "sdk": int(inventory.get("sdk") or 0),
                "companion_version": str(inventory.get("companion_version") or ""),
                "apps_available": int(inventory.get("apps_available") or 0),
                "apps_calibrated": int(inventory.get("apps_calibrated") or 0),
                "calibrations_stale": int(inventory.get("calibrations_stale") or 0),
                "availability_drift": list(inventory.get("availability_drift") or []),
            },
            "state_health": {
                "status": str(state_health.get("status") or "unknown"),
                "invalid": len(state_health.get("invalid") or []),
                "total_bytes": int(state_health.get("total_bytes") or 0),
                "backup_age_hours": state_health.get("backup_age_hours"),
                "wireguard_active": bool(state_health.get("wireguard_active")),
            },
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
    bank_tasks = snapshot.get("bank_tasks") or {}
    templates = snapshot.get("templates") or {}
    state_health = snapshot.get("state_health") or {}
    sync = snapshot.get("sync") or {}
    inventory = snapshot.get("inventory") or {}
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
        f"Банковские задачи: {bank_tasks.get('pending', 0)} · внимание: {bank_tasks.get('attention', 0)} · просрочены: {bank_tasks.get('overdue', 0)}",
        f"Шаблоны follow-up: {templates.get('count', 0)} · не обновлялись 30+ дн.: {templates.get('stale', 0)} · использований: {templates.get('used_total', 0)}",
        f"Таймеры: {timers_ok}/{len(timers)} активны · аудит: {snapshot.get('audit', {}).get('count', 0)} событий",
        f"Восстановление: {snapshot.get('recovery', {}).get('action', 'unknown')}",
        f"Состояние данных: {state_health.get('status', 'unknown')} · WireGuard: {'✅' if state_health.get('wireguard_active') else '⚠️'} · backup: {state_health.get('backup_age_hours', '—')} ч",
        f"Синхронизации: {sync.get('fresh', 0)}/{sync.get('total', 0)} свежие",
        f"Инвентарь: Android {inventory.get('android') or '—'} · SDK {inventory.get('sdk') or '—'} · калиброваны {inventory.get('apps_calibrated', 0)} · устарели {inventory.get('calibrations_stale', 0)}",
    ]
    if snapshot.get("issues"):
        lines.append("Проблемы: <code>" + ", ".join(str(value) for value in snapshot["issues"]) + "</code>")
    return "\n".join(lines)
