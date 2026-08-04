#!/usr/bin/env python3
"""Лёгкий health-check ключевых бизнес-сервисов AIOS.

Запускается таймером каждые пять минут. Telegram-уведомления отправляются
только при появлении/исчезновении проблемы, без постоянного спама.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "data" / "ops_health_state.json"
SERVICES = (
    "aios-telegram-bot.service",
    "aios-dashboard-v3.service",
    "aios-viber-desktop.service",
    "aios-viber-autoreply.service",
    "aios-signal-desktop.service",
    "aios-signal-autoreply.service",
    "aios-vnc-keepawake.service",
    "wg-quick@wg0.service",
    "aios-android-gateway.service",
    "aios-android-leads.timer",
    "aios-phone-control-digest.timer",
    "aios-phone-weekly-report.timer",
    "aios-messenger-profile-backup.timer",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _service_active(name: str) -> bool:
    return subprocess.run(["systemctl", "is-active", "--quiet", name], check=False).returncode == 0


def _mode(path: Path) -> int | None:
    try:
        return path.stat().st_mode & 0o777
    except OSError:
        return None


def _backup_age_hours() -> float | None:
    base = ROOT / "backups" / "messenger_profiles"
    try:
        archives = [p / "profiles.tar.gz" for p in base.iterdir() if p.is_dir() and (p / "profiles.tar.gz").exists()]
        latest = max(archives, key=lambda p: p.stat().st_mtime)
        return round((datetime.now(timezone.utc).timestamp() - latest.stat().st_mtime) / 3600, 1)
    except Exception:
        return None


def _android_probe() -> dict:
    """Probe/recover Android transport without reading screen or app data."""
    try:
        from aios_core.android_recovery import AndroidRecovery
        return AndroidRecovery(ROOT).check()
    except Exception:
        # Do not include transport exception text in a Telegram health alert:
        # it can contain network details and is not actionable for the owner.
        return {"registered": True, "adb_connected": False, "companion_connected": False,
                "reconnect_status": "error", "action": "phone_vpn_or_companion_needed"}


def collect(service_probe=_service_active, android_probe=None) -> dict:
    issues: list[str] = []
    warnings: list[str] = []
    service_states = {name: bool(service_probe(name)) for name in SERVICES}
    for name, active in service_states.items():
        if not active:
            issues.append(f"service:{name}")
    backup_age = _backup_age_hours()
    if backup_age is None:
        warnings.append("backup:не найден")
    elif backup_age > 30:
        issues.append(f"backup:устарел:{backup_age}ч")
    env_mode = _mode(ROOT / ".env")
    chrome_mode = _mode(ROOT / "data" / "chrome_twin" / "default")
    if env_mode is not None and env_mode > 0o600:
        issues.append(f"permissions:.env:{env_mode:o}")
    if chrome_mode is not None and chrome_mode > 0o700:
        issues.append(f"permissions:chrome:{chrome_mode:o}")
    # All phone workflow state is metadata-only but still private. Keep it
    # owner-readable only and surface a health issue if permissions drift.
    phone_private_files = {
        "phone_leads": ROOT / "data" / "android_gateway" / "lead_candidates.json",
        "phone_crm_followups": ROOT / "data" / "android_gateway" / "crm_followup_tasks.json",
        "phone_audit": ROOT / "data" / "android_gateway" / "action_audit.json",
        "phone_calibrations": ROOT / "data" / "android_gateway" / "app_ui_calibrations.json",
        "phone_recovery": ROOT / "data" / "android_gateway" / "recovery.json",
        "phone_lead_digest": ROOT / "data" / "android_gateway" / "lead_digest_state.json",
        "phone_daily_digest": ROOT / "data" / "android_gateway" / "phone_control_digest_state.json",
    }
    for label, path in phone_private_files.items():
        mode = _mode(path)
        if mode is not None and mode > 0o600:
            issues.append(f"permissions:{label}:{mode:o}")
    android = (android_probe or _android_probe)()
    if android.get("registered"):
        if not android.get("adb_connected"):
            issues.append("android:adb_offline")
        if not android.get("companion_connected"):
            issues.append("android:companion_offline")
    return {
        "status": "ok" if not issues else "degraded",
        "checked_at": _now(),
        "issues": sorted(issues),
        "warnings": sorted(warnings),
        "services": service_states,
        "backup_age_hours": backup_age,
        "android": android,
    }


def _load_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_name(f".{STATE.name}.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, STATE)


def _env(name: str) -> str:
    value = os.environ.get(name, "")
    if value:
        return value
    try:
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def _notify(text: str) -> None:
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat = _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return
    payload = json.dumps({"chat_id": int(chat), "text": text[:3800], "parse_mode": "HTML"}).encode()
    request = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=payload,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30):
        pass


def alert_if_changed(report: dict) -> dict:
    previous = _load_state()
    old_issues = set(previous.get("issues") or [])
    new_issues = set(report.get("issues") or [])
    created = sorted(new_issues - old_issues)
    resolved = sorted(old_issues - new_issues)
    if created:
        _notify("⚠️ <b>AIOS: требуется внимание</b>\n" + "\n".join(f"• {x}" for x in created))
    if resolved:
        _notify("✅ <b>AIOS: проблема устранена</b>\n" + "\n".join(f"• {x}" for x in resolved))
    _save_state({"checked_at": report.get("checked_at"), "issues": sorted(new_issues),
                 "warnings": report.get("warnings") or []})
    return {"created": created, "resolved": resolved}


def main() -> int:
    report = collect()
    if "--alert" in sys.argv:
        report["changes"] = alert_if_changed(report)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
