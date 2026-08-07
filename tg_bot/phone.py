"""Phone/Android: brain-gateway, workflows, leads, банк-монитор, uklon/easyway
(выделено из run_telegram_bot.py)."""
from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from tg_bot.common import PROJECT_ROOT, _esc_tg
from tg_bot.state import (
    _pending_confirm, _phone_route_drafts, _phone_brain_state,
    _last_phone_leads, _last_phone_crm_tasks, _last_bank_tasks,
)


_PHONE_BRAIN_API = os.environ.get("PHONE_BRAIN_API", "http://127.0.0.1:8790")


def _phone_brain_gateway_run(args: list[str], timeout: int) -> dict | None:
    """Выполнить команду Android-шлюза через очередь Phone Brain.

    Единая аренда устройства — никаких гонок процессов за ADB/экран.
    Возвращает dict как у legacy CLI, либо ``None``, если демон недоступен
    или команда не поддержана (тогда вызывающий код идёт legacy-путём).
    """
    import time as _time
    import urllib.request as _ureq

    plain = [str(a) for a in args if a != "--confirm"]
    command = plain[0] if plain else "status"
    confirmed = "--confirm" in args
    kind, payload = "", {}
    read_only = {"status", "apps", "profiles", "companion", "notifications", "accessibility",
                 "capture-status", "location-status", "files", "screenshot", "ui-dump", "audit"}
    if command in read_only and len(plain) == 1:
        kind, payload = "gateway.cli", {"command": command}
    elif command == "open" and len(plain) >= 2 and confirmed:
        kind, payload = "app.open", {"package": plain[1], "confirm": True}
    elif command == "location" and confirmed:
        kind, payload = "device.location", {"confirm": True}
    elif command == "pull" and len(plain) >= 2 and confirmed:
        kind, payload = "device.pull", {"path": plain[1], "confirm": True}
    else:
        return None  # команда не замаплена — legacy-путь

    now = _time.monotonic()
    if _phone_brain_state["ok"] is False and now - _phone_brain_state["checked"] < 20:
        return None

    def _api(method: str, path: str, body: dict | None = None, req_timeout: float = 4.0) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = _ureq.Request(_PHONE_BRAIN_API + path, data=data, method=method,
                                headers={"Content-Type": "application/json"})
        with _ureq.urlopen(request, timeout=req_timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        created = _api("POST", "/jobs", {"kind": kind, "payload": payload})
        job_id = int((created.get("job") or {}).get("id") or 0)
        if not job_id:
            return None
        _phone_brain_state.update(ok=True, checked=now)
    except Exception:
        _phone_brain_state.update(ok=False, checked=now)
        return None

    deadline = now + max(5, min(int(timeout), 240))
    while _time.monotonic() < deadline:
        try:
            job = _api("GET", f"/jobs/{job_id}").get("job") or {}
        except Exception:
            return None
        status = job.get("status")
        if status == "done":
            result = job.get("result") or {}
            if kind == "gateway.cli":
                output = result.get("output")
                if isinstance(output, dict):
                    return output
                return {"status": "error", "error": "пустой ответ очереди"}
            output = {"status": "ok"}
            for key, value in result.items():
                if key != "status":
                    output[key] = value
            return output
        if status in ("failed", "need_confirm", "cancelled"):
            return {"status": "error",
                    "error": str(job.get("error") or (job.get("result") or {}).get("error") or status)[:200]}
        _time.sleep(0.8)
    return {"status": "error", "error": "таймаут ожидания задачи Phone Brain"}


def _android_gateway_run(args: list[str], timeout: int = 60) -> dict:
    """Вызвать Android gateway и разобрать JSON без shell-инъекций.

    Сначала — через очередь Phone Brain (единая аренда устройства, нет гонок
    с задачами демона); при недоступности демона — legacy subprocess CLI.
    """
    via_brain = _phone_brain_gateway_run(args, timeout)
    if via_brain is not None:
        return via_brain
    import subprocess as _sp
    try:
        result = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_android_gateway.py"), *args],
                         capture_output=True, text=True, timeout=timeout, cwd=str(PROJECT_ROOT),
                         env={**os.environ, "AIOS_ADB_BIN": "/usr/local/bin/aios-adb"})
        out = (result.stdout or "").strip()
        start = out.find("{")
        return json.loads(out[start:]) if start >= 0 else {"status": "error", "error": (result.stderr or out)[-250:]}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}


def _phone_brain_api_request(method: str, path: str, body: dict | None = None,
                             req_timeout: float = 4.0) -> dict:
    """Прямой вызов локального API Phone Brain (мониторинг и одобрения)."""
    import urllib.request as _ureq2
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = _ureq2.Request(_PHONE_BRAIN_API + path, data=data, method=method,
                             headers={"Content-Type": "application/json"})
    try:
        with _ureq2.urlopen(request, timeout=req_timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:160]}


def _handle_phone_brain_intent(api, chat_id: int, text: str) -> bool:
    """«мозг» — статус Phone Brain; «черновики» — очередь на одобрение;
    «подтверди N» — одобрить черновик (цикл автономных ответов клиентам)."""
    import re as _re2
    t = " ".join(str(text or "").casefold().split())
    approve = _re2.match(r"^(?:подтверди|подтвердить|підтверди|confirm)\s+([0-9]{1,9})\b", t)
    if approve:
        job_id = int(approve.group(1))
        result = _phone_brain_api_request("POST", f"/jobs/{job_id}/confirm", {})
        if result.get("status") == "ok":
            api.send_message(chat_id, f"✅ Черновик #{job_id} подтверждён — отправлен в работу.")
        else:
            api.send_message(chat_id, f"⚠️ #{job_id}: {_esc_tg(result.get('error') or 'ошибка демона')}")
        return True
    if any(term in t for term in ("черновики телефона", "список черновиков", "черновики",
                                  "на одобрение")):
        data = _phone_brain_api_request("GET", "/jobs?status=need_confirm&limit=10")
        if data.get("status") == "error":
            api.send_message(chat_id, "⚠️ Phone Brain недоступен (демон не отвечает).")
            return True
        jobs = data.get("jobs") or []
        if not jobs:
            api.send_message(chat_id, "📭 Черновиков на одобрение нет.")
            return True
        lines = [f"✉️ <b>Черновиков на одобрение: {len(jobs)}</b>"]
        for job in jobs[-10:]:
            action = str((job.get("result") or {}).get("action") or job.get("kind") or "")
            lines.append(f"• #{job.get('id')} <code>{_esc_tg(str(job.get('kind') or ''))}</code>"
                         f" — {_esc_tg(action[:60])}")
        lines.append("Подтвердить: «подтверди N» (например, «подтверди %s»)."
                     % (jobs[0].get("id") or "N"))
        api.send_message(chat_id, "\n".join(lines))
        return True
    if any(term in t for term in ("мозг", "статус мозга", "phone brain", "мозг телефона",
                                  "статус демона телефона")):
        health = _phone_brain_api_request("GET", "/health")
        if health.get("status") == "error":
            api.send_message(chat_id, "⚠️ Phone Brain недоступен (демон не отвечает).")
            return True
        daemon = health.get("daemon") or {}
        device = (health.get("device") or {}).get("device") or {}
        brain = (health.get("device") or {}).get("brain") or {}
        queue = health.get("queue") or {}
        uptime = int(daemon.get("uptime_seconds") or 0)
        connected = "🟢 онлайн" if device.get("connected") else "🔴 офлайн"
        backoff = brain.get("backoff_seconds")
        extra = (f", reconnect через {backoff}с"
                 if not device.get("connected") and backoff else "")
        qparts = " · ".join(f"{k}:{v}" for k, v in sorted(queue.items()) if v) or "пусто"
        reactions = _phone_brain_api_request("GET", "/reactions")
        rules_n = len([r for r in (reactions.get("rules") or []) if r.get("id")])
        api.send_message(
            chat_id,
            "🧠 <b>Phone Brain</b> v%s\n"
            "Аптайм: %dм %dс · занятая задача: %s\n"
            "Очередь: %s\n"
            "Устройство: %s%s · правил реакций: %d\n"
            "Команды: «черновики» · «подтверди N»"
            % (_esc_tg(str(health.get("version") or "?")), uptime // 60, uptime % 60,
               daemon.get("busy_job") or "—", _esc_tg(qparts), connected, _esc_tg(extra),
               rules_n))
        return True
    return False


def _handle_phone_workflow_readiness_intent(api, chat_id: int, text: str) -> bool:
    t = " ".join(str(text or "").casefold().split())
    if not any(phrase in t for phrase in ("проверка сценариев телефона", "готовность сценариев", "тест сценариев телефона")):
        return False
    try:
        from aios_core.phone_workflow_readiness import PhoneWorkflowReadiness, format_telegram
        api.send_message(chat_id, format_telegram(PhoneWorkflowReadiness(PROJECT_ROOT).snapshot()))
    except Exception:
        api.send_message(chat_id, "⚠️ Проверка сценариев телефона временно недоступна.")
    return True


def _handle_phone_jobs_intent(api, chat_id: int, text: str) -> bool:
    t = " ".join(str(text or "").casefold().split())
    if not any(phrase in t for phrase in ("планировщик телефона", "статус jobs телефона", "задачи планировщика телефона", "dry run jobs телефона")):
        return False
    try:
        from aios_core.phone_jobs import PhoneJobs
        jobs = PhoneJobs(PROJECT_ROOT)
        report = jobs.dry_run() if "dry run" in t else jobs.snapshot()
        if "dry run" in t:
            valid = sum(1 for item in report.get("jobs") or [] if item.get("valid"))
            api.send_message(chat_id, f"🧪 <b>Dry-run jobs телефона</b>\nСкриптов проверено: {valid}/{len(report.get('jobs') or [])}")
        else:
            backup = report.get("backup") or {}
            api.send_message(chat_id,
                             "⏱ <b>Планировщик телефона</b>\n"
                             f"Jobs: {report.get('active', 0)}/{report.get('total', 0)} · статус: {report.get('status')}\n"
                             f"Android config backup: {backup.get('count', 0)} · retention: {'✅' if backup.get('retention_ok', True) else '⚠️'} · JSON проблем: {backup.get('invalid', 0)}")
    except Exception:
        api.send_message(chat_id, "⚠️ Статус jobs телефона временно недоступен.")
    return True


def _handle_phone_inventory_intent(api, chat_id: int, text: str) -> bool:
    t = " ".join(str(text or "").casefold().split())
    if not any(phrase in t for phrase in ("инвентарь телефона", "версии телефона", "версии android", "профили телефона")):
        return False
    try:
        from aios_core.phone_inventory import PhoneInventory
        report = PhoneInventory(PROJECT_ROOT).record()
        drift = report.get("availability_drift") or []
        api.send_message(chat_id,
                         "📦 <b>Инвентарь телефона</b>\n"
                         f"Android: {report.get('android') or '—'} · SDK: {report.get('sdk') or '—'}\n"
                         f"Companion: {report.get('companion_version') or '—'}\n"
                         f"Приложения: {report.get('apps_available', 0)} доступны · {report.get('apps_calibrated', 0)} калиброваны · устарели: {report.get('calibrations_stale', 0)}\n"
                         f"WireGuard: {'✅' if report.get('wireguard_active') else '⚠️'}"
                         + (f"\nИзменения доступности: {', '.join(map(str, drift))}" if drift else ""))
    except Exception:
        api.send_message(chat_id, "⚠️ Инвентарь телефона временно недоступен.")
    return True


def _handle_phone_metrics_intent(api, chat_id: int, text: str) -> bool:
    t = " ".join(str(text or "").casefold().split())
    if not any(phrase in t for phrase in ("тренды телефона", "тренд телефона", "экспорт метрик телефона", "метрики телефона", "калибровки телефона", "статус калибровок")):
        return False
    try:
        from aios_core.phone_metrics import PhoneMetricsStore
        store = PhoneMetricsStore(PROJECT_ROOT)
        if "экспорт" in t:
            target = store.export_csv()
            api.send_document(chat_id, str(target), caption="📈 Метрики телефона · агрегированные данные")
            return True
        if "калибров" in t:
            report = store.calibration_report()
            rows = report.get("apps") or []
            text = "🧩 <b>Калибровки приложений</b>\n" + ("\n".join(
                f"• {row.get('profile')}: {'✅ готово' if row.get('ready') else '⚠️ частично'} · элементов: {row.get('selectors', 0)}"
                for row in rows
            ) if rows else "Калибровок пока нет.")
            api.send_message(chat_id, text)
            return True
        trend = store.trend(limit=7)
        availability = store.availability(limit=30)
        changes = trend.get("changes") or {}
        api.send_message(chat_id,
                         "📈 <b>Тренды телефона</b>\n"
                         f"Снимков: {trend.get('snapshots', 0)} · ADB: {availability.get('adb_pct', 0)}% · Companion: {availability.get('companion_pct', 0)}%\n"
                         f"Лиды: {changes.get('leads_pending', 0):+d} · CRM follow-up: {changes.get('crm_open', 0):+d}\n"
                         f"Банковские задачи: {changes.get('bank_tasks', 0):+d} · калиброванные приложения: {changes.get('apps_calibrated', 0):+d}\n"
                         "<i>Экспорт содержит только агрегаты, без чатов, имён, номеров, координат и текстов.</i>")
    except Exception:
        api.send_message(chat_id, "⚠️ Метрики телефона временно недоступны.")
    return True


def _handle_phone_bank_monitor_intent(api, chat_id: int, text: str) -> bool:
    raw = str(text or "").strip()
    t = " ".join(raw.casefold().split())
    task_scope = any(phrase in t for phrase in ("банковские задачи", "задачи банков", "задачи банка"))
    review = re.search(r"(?:отметь|закрой|обработай)\s+банковск\w*\s+задач\w*\s*#?(\d+)", raw, re.IGNORECASE)
    bank_scope = any(phrase in t for phrase in ("банки телефона", "статус банков телефона", "банковские уведомления телефона", "банки android"))
    if not (task_scope or review or bank_scope or (chat_id in _last_bank_tasks and "банковск" in t)):
        return False
    try:
        from aios_core.android_bank_monitor import AndroidBankMonitor, format_telegram
        monitor = AndroidBankMonitor(PROJECT_ROOT)
        if review:
            tasks = _last_bank_tasks.get(chat_id) or []
            index = int(review.group(1))
            if not 1 <= index <= len(tasks):
                api.send_message(chat_id, "ℹ️ Сначала откройте «банковские задачи телефона», затем укажите номер.")
                return True
            _pending_confirm[chat_id] = {"kind": "bank_task_review", "data": {"task_id": tasks[index - 1].get("id")}}
            api.send_message(chat_id, "🏦 Отметить локальную задачу банковского уведомления обработанной?\n«да» / «нет»")
            return True
        if task_scope:
            tasks = monitor.list_tasks(limit=30)
            _last_bank_tasks[chat_id] = tasks
            if not tasks:
                api.send_message(chat_id, "🏦 <b>Банковские задачи телефона</b>\nОткрытых задач на проверку нет.")
                return True
            summary = monitor.task_summary()
            lines = [
                "🏦 <b>БАНКОВСКИЕ ЗАДАЧИ ТЕЛЕФОНА</b>",
                f"<i>Открыты: {summary.get('pending', len(tasks))} · внимание: {summary.get('attention', 0)} · просрочены: {summary.get('overdue', 0)}</i>",
                "━━━━━━━━━━━━━━━━",
            ]
            age_label = {"fresh": "🟢 Новая", "attention": "🟠 Внимание", "overdue": "🔴 Просрочена", "unknown": "⚪ Без времени"}
            for index, task in enumerate(tasks[:12], 1):
                source = _esc_tg(str(task.get("source") or "Банк"))
                observed = _esc_tg(str(task.get("observed_at") or "")[:19])
                age = age_label.get(str(task.get("age_state") or ""), "⚪ Без времени")
                lines.append(f"{index:02d}. <b>{source}</b> · {age} · 🕐 {observed}")
            lines.append("━━━━━━━━━━━━━━━━")
            lines.append("<i>«отметь банковскую задачу 1 обработанной» — закрыть локальную задачу. Суммы, карты и OTP не выводятся.</i>")
            api.send_message(chat_id, "\n".join(lines)[:3900])
            return True
        api.send_message(chat_id, format_telegram(monitor.snapshot()))
    except Exception:
        api.send_message(chat_id, "⚠️ Безопасный статус банков телефона временно недоступен.")
    return True


def _handle_phone_recovery_intent(api, chat_id: int, text: str) -> bool:
    t = " ".join(str(text or "").casefold().split())
    data_scope = any(phrase in t for phrase in ("здоровье данных телефона", "состояние данных телефона", "проверка данных телефона"))
    sync_scope = any(phrase in t for phrase in ("статус синхронизации телефона", "синхронизации телефона", "проверка синхронизации телефона"))
    if not (data_scope or sync_scope or any(phrase in t for phrase in ("восстановление телефона", "диагностика телефона", "почини телефон", "проверка adb"))):
        return False
    try:
        if sync_scope:
            from aios_core.phone_sync_status import PhoneSyncStatus
            report = PhoneSyncStatus(PROJECT_ROOT).snapshot()
            lines = ["🔄 <b>Синхронизации телефона</b>", f"Свежие: {report.get('fresh', 0)}/{report.get('total', 0)}"]
            for item in (report.get('sources') or [])[:10]:
                age = item.get('age_minutes')
                lines.append(f"• {item.get('id')}: {'✅' if item.get('exists') else '⚪'} · {str(age) + ' мин' if age is not None else 'нет времени'}")
            api.send_message(chat_id, "\n".join(lines))
            return True
        if data_scope:
            from aios_core.phone_state_health import PhoneStateHealth
            report = PhoneStateHealth(PROJECT_ROOT).snapshot()
            api.send_message(chat_id,
                             "🗄 <b>Состояние данных телефона</b>\n"
                             f"Статус: {'✅' if report.get('status') == 'ok' else '⚠️'}\n"
                             f"WireGuard: {'✅' if report.get('wireguard_active') else '⚠️'} · backup: {report.get('backup_age_hours', '—')} ч\n"
                             f"Файлов состояния: {len(report.get('files') or [])} · проблем JSON: {len(report.get('invalid') or [])} · размер: {report.get('total_bytes', 0)} байт")
            return True
        from aios_core.android_recovery import AndroidRecovery
        report = AndroidRecovery(PROJECT_ROOT).check()
        action = str(report.get("action") or "unknown")
        labels = {
            "none": "✅ Подключение ADB и AIOS Companion работают штатно.",
            "wireless_debug_endpoint_needed": "⚠️ Companion доступен, но требуется новый endpoint Беспроводной отладки.",
            "companion_restart_needed": "⚠️ ADB подключён, но AIOS Companion недоступен. Откройте Companion или перезапустите его на телефоне.",
            "phone_vpn_or_companion_needed": "⚠️ Телефон или WireGuard/Companion недоступны. Проверьте VPN и подключение телефона.",
        }
        api.send_message(chat_id, "🛠 <b>Восстановление телефона</b>\n" + labels.get(action, "⚠️ Нужна проверка подключения."))
    except Exception:
        api.send_message(chat_id, "⚠️ Диагностика телефона временно недоступна.")
    return True


def _handle_phone_weekly_report_intent(api, chat_id: int, text: str) -> bool:
    t = " ".join(str(text or "").casefold().split())
    if not any(phrase in t for phrase in ("недельный отчёт телефона", "недельный отчет телефона", "отчёт лидов за неделю", "отчет лидов за неделю", "недельная сводка телефона")):
        return False
    try:
        from run_phone_weekly_report import build_text
        api.send_message(chat_id, build_text(PROJECT_ROOT, days=7))
    except Exception:
        api.send_message(chat_id, "⚠️ Недельный отчёт телефона временно недоступен.")
    return True


def _handle_phone_control_center_intent(api, chat_id: int, text: str) -> bool:
    t = " ".join(str(text or "").casefold().split())
    if not any(phrase in t for phrase in ("центр телефона", "статус автоматизации телефона", "контроль телефона", "центр android")):
        return False
    try:
        from aios_core.phone_control_center import PhoneControlCenter, format_telegram
        api.send_message(chat_id, format_telegram(PhoneControlCenter(PROJECT_ROOT).snapshot()))
    except Exception:
        api.send_message(chat_id, "⚠️ Центр управления телефоном временно недоступен.")
    return True


def _handle_phone_audit_intent(api, chat_id: int, text: str) -> bool:
    """Render the metadata-only phone action log on explicit owner request."""
    t = " ".join(str(text or "").casefold().split())
    if not any(phrase in t for phrase in ("журнал телефона", "аудит телефона", "действия телефона", "логи телефона")):
        return False
    from aios_core.android_audit import PhoneActionAudit
    events = PhoneActionAudit(PROJECT_ROOT).recent(limit=20)
    if not events:
        api.send_message(chat_id, "📋 <b>Журнал телефона</b>\nБезопасных действий пока не зарегистрировано.")
        return True
    labels = {
        "app_open": "Открытие приложения", "app_ui_calibration": "Калибровка интерфейса",
        "messenger_chat_open": "Открытие чата", "messenger_draft": "Черновик сообщения",
        "messenger_send": "Отправка сообщения", "uklon_route": "Черновик Uklon",
        "uklon_route_query": "Поиск Uklon", "easyway_route": "Черновик EasyWay",
        "easyway_route_query": "Поиск EasyWay",
    }
    lines = ["📋 <b>БЕЗОПАСНЫЙ ЖУРНАЛ ТЕЛЕФОНА</b>", "━━━━━━━━━━━━━━━━"]
    for index, event in enumerate(events[-15:][::-1], 1):
        action = labels.get(str(event.get("action") or ""), str(event.get("action") or "действие"))
        status = _esc_tg(str(event.get("status") or "—"))
        package = _esc_tg(str(event.get("package") or ""))
        at = _esc_tg(str(event.get("at") or "")[:19])
        lines.append(f"{index:02d}. <b>{_esc_tg(action)}</b> · {status}" + (f" · <code>{package}</code>" if package else ""))
        lines.append(f"    🕐 {at}")
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append("<i>Журнал не содержит текста сообщений, имён, маршрутов, координат, фото, аудио или координат нажатий.</i>")
    api.send_message(chat_id, "\n".join(lines)[:3900])
    return True


def _phone_lead_queue():
    from aios_core.android_leads import AndroidLeadQueue
    return AndroidLeadQueue(PROJECT_ROOT)


def _followup_templates():
    from aios_core.followup_templates import FollowupTemplateStore
    return FollowupTemplateStore(PROJECT_ROOT)


def _handle_phone_lead_intent(api, chat_id: int, text: str) -> bool:
    """Privacy-preserving queue for WhatsApp/iMe notification contacts."""
    raw = str(text or "").strip()
    t = " ".join(raw.casefold().split())
    has_phone_scope = any(word in t for word in (
        "телефон", "android", "андроид", "whatsapp", "ватсап", "ime", "i.me", "айми", "име",
    ))
    has_lead_scope = any(stem in t for stem in ("лид", "обращен", "потенциальн"))
    has_task_scope = any(phrase in t for phrase in ("crm задач", "crm-задач", "crm follow", "follow-up", "задачи телефона"))
    has_template_scope = any(phrase in t for phrase in ("шаблон follow", "шаблоны follow", "шаблон ответа", "шаблоны ответов"))
    # Follow-up commands may omit «телефон» only after this chat received a
    # metadata-only list. Template management is private local configuration.
    if not (has_template_scope or ((has_lead_scope or has_task_scope) and (has_phone_scope or chat_id in _last_phone_leads or chat_id in _last_phone_crm_tasks))):
        return False
    queue = _phone_lead_queue()
    templates = _followup_templates()
    template_add = re.search(r"(?:добавь|сохрани)\s+шаблон(?:\s+follow[- ]?up|\s+ответа)?\s*:\s*([^|]{1,80})\|\s*(.+)$", raw, re.IGNORECASE)
    if template_add:
        result = templates.upsert(template_add.group(1).strip(), template_add.group(2).strip())
        if result.get("status") in ("created", "updated"):
            api.send_message(chat_id, f"✅ Шаблон follow-up «{_esc_tg(result.get('name'))}» сохранён локально.")
        else:
            api.send_message(chat_id, f"⚠️ Шаблон не сохранён: {_esc_tg(result.get('error') or '?')}")
        return True
    if has_template_scope and not has_task_scope:
        rows = templates.list()
        if not rows:
            api.send_message(chat_id, "📝 <b>Шаблоны follow-up</b>\nШаблонов пока нет.")
        else:
            api.send_message(chat_id, "📝 <b>Шаблоны follow-up</b>\n" + "\n".join(f"• {_esc_tg(row.get('name'))}" for row in rows[:30]))
        return True
    template_draft = re.search(
        r"(?:подготовь|сделай)\s+шаблон\s+(.+?)\s+(?:по|для)\s+(?:crm\s*)?задач\w*\s*#?(\d+)\s+"
        r"(?:в\s+)?(whatsapp|ватсап|ватс\s*апп|вотсап|ime|i\.me|айми|име)\s*:\s*(.+)$",
        raw, re.IGNORECASE,
    )
    if template_draft:
        template = templates.get(template_draft.group(1).strip())
        tasks = _last_phone_crm_tasks.get(chat_id) or []
        index = int(template_draft.group(2))
        if not template:
            api.send_message(chat_id, "ℹ️ Шаблон не найден. Откройте «шаблоны follow-up» или добавьте его.")
            return True
        if not 1 <= index <= len(tasks):
            api.send_message(chat_id, "ℹ️ Сначала откройте «CRM задачи телефона», затем укажите номер задачи.")
            return True
        app_token = template_draft.group(3).casefold()
        app = "ime" if app_token in ("ime", "i.me", "айми", "име") else "whatsapp"
        contact = template_draft.group(4).strip()
        # Audit only template selection metadata, never its name or text.
        templates.mark_used(template_draft.group(1).strip())
        try:
            from aios_core.android_audit import PhoneActionAudit
            PhoneActionAudit(PROJECT_ROOT).record("followup_template", "selected")
        except Exception:
            pass
        _pending_confirm[chat_id] = {"kind": "phone_crm_task_draft", "data": {
            "task_id": tasks[index - 1].get("id"), "app": app, "contact": contact, "text": template.get("text") or "",
        }}
        api.send_message(chat_id, "✍️ Открыть указанный чат и вставить выбранный шаблон follow-up? Отправка потребует отдельного подтверждения. «да» / «нет»")
        return True
    draft_from_task = re.search(
        r"(?:подготовь|сделай)\s+(?:черновик|ответ)\s+(?:по|для)\s+(?:crm\s*)?задач\w*\s*#?(\d+)\s+"
        r"(?:в\s+)?(whatsapp|ватсап|ватс\s*апп|вотсап|ime|i\.me|айми|име)\s*:\s*([^|]{1,100})\|\s*(.+)$",
        raw, re.IGNORECASE,
    )
    if draft_from_task:
        tasks = _last_phone_crm_tasks.get(chat_id) or []
        index = int(draft_from_task.group(1))
        if not 1 <= index <= len(tasks):
            api.send_message(chat_id, "ℹ️ Сначала откройте «CRM задачи телефона», затем укажите номер задачи.")
            return True
        app_token = draft_from_task.group(2).casefold()
        app = "ime" if app_token in ("ime", "i.me", "айми", "име") else "whatsapp"
        contact = draft_from_task.group(3).strip()
        body = draft_from_task.group(4).strip()
        if not contact or not body:
            api.send_message(chat_id, "ℹ️ Формат: «подготовь черновик по CRM задаче 1 в WhatsApp: Имя | Текст»")
            return True
        _pending_confirm[chat_id] = {"kind": "phone_crm_task_draft", "data": {
            "task_id": tasks[index - 1].get("id"), "app": app, "contact": contact, "text": body,
        }}
        api.send_message(chat_id,
                         "✍️ Открыть указанный чат и вставить черновик из CRM follow-up задачи?\n"
                         "Открытие чата может отметить его прочитанным; отправка потребует отдельного подтверждения. «да» / «нет»")
        return True
    complete = re.search(r"(?:закрой|заверши|выполни)\s+(?:crm\s*)?(?:задач\w*|follow[- ]?up)\s*#?(\d+)", raw, re.IGNORECASE)
    if complete:
        tasks = _last_phone_crm_tasks.get(chat_id) or []
        index = int(complete.group(1))
        if not 1 <= index <= len(tasks):
            api.send_message(chat_id, "ℹ️ Сначала откройте «CRM задачи телефона», затем укажите номер задачи.")
            return True
        _pending_confirm[chat_id] = {"kind": "phone_crm_task_complete", "data": {"task_id": tasks[index - 1].get("id")}}
        api.send_message(chat_id, "✅ Закрыть локальную CRM follow-up задачу?\n«да» / «нет»")
        return True
    if has_task_scope and not has_lead_scope:
        tasks = queue.list_crm_tasks(limit=30)
        _last_phone_crm_tasks[chat_id] = tasks
        if not tasks:
            api.send_message(chat_id, "📌 <b>CRM задачи телефона</b>\nОткрытых follow-up задач нет.")
            return True
        summary = queue.summary()
        lines = [
            "📌 <b>CRM FOLLOW-UP ЗАДАЧИ ТЕЛЕФОНА</b>",
            f"<i>Открыты: {summary.get('crm_open', len(tasks))} · внимание: {summary.get('crm_attention', 0)} · просрочены: {summary.get('crm_overdue', 0)}</i>",
            "━━━━━━━━━━━━━━━━",
        ]
        age_label = {"fresh": "🟢 Новая", "attention": "🟠 Внимание", "overdue": "🔴 Просрочена", "unknown": "⚪ Без времени"}
        for index, task in enumerate(tasks[:12], 1):
            source = _esc_tg(str(task.get("source") or "Телефон"))
            created = _esc_tg(str(task.get("created_at") or "")[:19])
            age = age_label.get(str(task.get("age_state") or ""), "⚪ Без времени")
            lines.append(f"╭─ <code>{index:02d}</code> 📌 <b>{source}</b> · {age}")
            lines.append("├ Открыть чат и вручную проверить обращение")
            lines.append(f"╰ 🕐 {created or 'время недоступно'}")
        lines.append("━━━━━━━━━━━━━━━━")
        lines.append("<i>«закрой CRM задачу 1» — закрыть локальную follow-up задачу. Клиенты и сообщения не создаются автоматически.</i>")
        api.send_message(chat_id, "\n".join(lines)[:3900])
        return True
    promote = re.search(r"(?:создай|добавь)\s+(?:crm\s*)?(?:задач\w*)\s+(?:для\s+)?(?:лид\w*|обращени\w*)\s*(?:телефона)?\s*#?(\d+)", raw, re.IGNORECASE)
    if promote:
        rows = _last_phone_leads.get(chat_id) or []
        index = int(promote.group(1))
        if not 1 <= index <= len(rows):
            api.send_message(chat_id, "ℹ️ Сначала откройте «лиды телефона», затем укажите номер карточки.")
            return True
        _pending_confirm[chat_id] = {"kind": "phone_lead_promote", "data": {"lead_id": rows[index - 1].get("id")}}
        api.send_message(chat_id,
                         "📌 Создать локальную CRM-задачу для этой карточки?\n"
                         "Клиент, имя, телефон и сообщение не будут созданы или переданы. «да» / «нет»")
        return True
    review = re.search(r"(?:обработай|отметь|закрой)\s+(?:лид|обращени\w*)\s*(?:телефона)?\s*#?(\d+)", raw, re.IGNORECASE)
    if review:
        rows = _last_phone_leads.get(chat_id) or []
        index = int(review.group(1))
        if not 1 <= index <= len(rows):
            api.send_message(chat_id, "ℹ️ Сначала откройте «лиды телефона», затем укажите номер карточки.")
            return True
        result = queue.review(str(rows[index - 1].get("id") or ""))
        if result.get("status") in ("reviewed", "already_reviewed"):
            api.send_message(chat_id, "✅ Лид отмечен как обработанный. CRM-клиент и сообщения не создавались.")
        else:
            api.send_message(chat_id, "⚠️ Не удалось обновить карточку лида.")
        return True
    # Refresh only the metadata-only queue; notification text/senders are never
    # requested or rendered by this handler.
    queue.sync()
    source = "WhatsApp" if any(word in t for word in ("whatsapp", "ватсап")) else \
             "iMe" if any(word in t for word in ("ime", "i.me", "айми", "име")) else ""
    rows = queue.list_pending(limit=20, source=source)
    _last_phone_leads[chat_id] = rows
    if not rows:
        api.send_message(chat_id, "📲 <b>Лиды телефона</b>\nНовых карточек для проверки нет.")
        return True
    summary = queue.summary()
    lines = ["📲 <b>ПОТЕНЦИАЛЬНЫЕ ЛИДЫ ТЕЛЕФОНА</b>",
             f"<i>Ожидают проверки: {summary.get('pending', len(rows))} · CRM-задач: {summary.get('crm_open', 0)}</i>",
             "━━━━━━━━━━━━━━━━"]
    for index, row in enumerate(rows[:12], 1):
        source_label = _esc_tg(str(row.get("source") or "Телефон"))
        observed = _esc_tg(str(row.get("observed_at") or "")[:19])
        lines.append(f"╭─ <code>{index:02d}</code> 📲 <b>{source_label}</b>")
        lines.append("├ Потенциальное новое обращение")
        lines.append(f"╰ 🕐 {observed or 'время недоступно'}")
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append("<i>Содержимое уведомлений, имена и номера не сохраняются здесь. «отметь лид 1 обработанным» — закрыть карточку; «создай CRM задачу для лида 1» — создать локальную follow-up задачу.</i>")
    api.send_message(chat_id, "\n".join(lines)[:3900])
    return True


def _phone_adapter(key: str):
    """Load a confirmed-workflow adapter without exposing Companion secrets."""
    from aios_core.android_gateway import AndroidGateway
    from aios_core.android_phone_workflows import adapter_for
    return adapter_for(key, AndroidGateway(PROJECT_ROOT))


def _phone_error(data: dict) -> str:
    """Safe error renderer: adapters must never return raw screen text here."""
    return _esc_tg(str(data.get("error") or data.get("status") or "неизвестная ошибка"))[:280]


def _mask_android_notification(value: object, limit: int = 180) -> str:
    """Never echo OTP/PIN/card-like data from a phone notification to Telegram."""
    value = str(value or "")
    value = re.sub(r"(?<!\d)(?:\d[ -]?){12,19}(?!\d)", "••••", value)
    value = re.sub(r"(?<!\d)\d{4,8}(?!\d)", "••••", value)
    return value[:limit]


def _send_phone_status(api, chat_id: int, adapter) -> None:
    data = adapter.status()
    title = _esc_tg(str(data.get("title") or "Приложение"))
    if data.get("status") == "not_installed":
        api.send_message(chat_id, f"➕ <b>{title}</b> не найден на телефоне.")
        return
    if data.get("status") != "ok":
        api.send_message(chat_id, f"⚠️ <b>{title}</b>: {_phone_error(data)}")
        return
    lines = [f"📱 <b>{title}</b>",
             f"Приложение: <b>{'доступно' if data.get('available') else 'не найдено'}</b>",
             f"Управление интерфейсом: <b>{'готово' if data.get('accessibility') else 'не разрешено'}</b>",
             f"Сейчас активно: <b>{'да' if data.get('active') else 'нет'}</b>"]
    if "notification_count" in data:
        lines.append(f"Новых служебных уведомлений: <b>{data.get('notification_count', 0)}</b>")
    if data.get("ui_calibrated"):
        controls = data.get("route_controls") or {}
        ready = bool(controls) and all(bool(value) for value in controls.values())
        lines.append("Интерфейс маршрута: <b>проверен</b>" if ready else "Интерфейс маршрута: <b>требует проверки</b>")
    capabilities = data.get("route_capabilities") or {}
    if capabilities:
        extended = all(bool(capabilities.get(key)) for key in ("alternate_pickup", "multi_stop_add", "multi_stop_delete", "multi_stop_reorder"))
        lines.append("Серия адресов: <b>готова</b>" if extended else "Серия адресов: <b>требует проверки</b>")
        lines.append("Автозаказ: <b>отключён</b>")
    if not data.get("ui_ready"):
        lines.append("⚠️ Для безопасной работы с интерфейсом требуется обновить AIOS Companion.")
    api.send_message(chat_id, "\n".join(lines))


def _uklon_route_field_allowed(field: str) -> bool:
    value = str(field or "").casefold()
    return value in {"pickup", "destination"} or bool(re.fullmatch(r"stop_[1-9][0-9]*", value))


def _uklon_route_field_label(field: str) -> str:
    value = str(field or "")
    if value == "pickup":
        return "точку отправления"
    if value == "destination":
        return "конечную точку"
    match = re.fullmatch(r"stop_([1-9][0-9]*)", value)
    return f"остановку №{match.group(1)}" if match else "точку маршрута"


def _uklon_next_route_field(field: str, route: dict) -> str:
    value = str(field or "")
    stops = list(route.get("stops") or [])
    if value == "pickup":
        return "stop_1" if stops else "destination"
    match = re.fullmatch(r"stop_([1-9][0-9]*)", value)
    if match:
        index = int(match.group(1))
        return f"stop_{index + 1}" if index < len(stops) else "destination"
    return ""


def _parse_uklon_route_request(raw: str) -> dict | None:
    """Parse a safe route draft request without selecting addresses or booking."""
    match = re.search(
        r"(?:маршрут|поездк\w*)\s+(?:uklon|уклон)\s*[:—–-]?\s*(.+)$",
        str(raw or "").strip(),
        re.IGNORECASE,
    )
    if not match:
        return None
    payload = match.group(1).strip()
    if payload.casefold().startswith(("до ", "в ")):
        return {"pickup": "", "stops": [], "destination": payload.split(" ", 1)[1].strip()}
    parts = [part.strip() for part in re.split(r"\s*(?:->|→)\s*", payload)]
    if len(parts) >= 2:
        if parts[0]:
            return {"pickup": parts[0], "stops": [part for part in parts[1:-1] if part], "destination": parts[-1]}
        return {"pickup": "", "stops": [part for part in parts[1:-1] if part], "destination": parts[-1]}
    legacy = re.match(r"^(.+?)\s+(?:до|в)\s+(.+)$", payload, re.IGNORECASE)
    if legacy:
        return {"pickup": legacy.group(1).strip(), "stops": [], "destination": legacy.group(2).strip()}
    return None


def _handle_android_phone_workflow_intent(api, chat_id: int, text: str) -> bool:
    """Intent router for confirmation-gated phone app workflows.

    It deliberately runs before the generic Android app opener.  A phrase such
    as «открой чат WhatsApp» must not be reduced to an unscoped package launch.
    """
    raw = str(text or "").strip()
    t = " ".join(raw.casefold().split())
    if not t:
        return False
    whatsapp_words = ("whatsapp", "ватсап", "ватс апп", "вотсап", "watsapp")
    ime_words = ("ime", "i.me", "айми", "име мессенджер")
    easyway_words = ("easyway", "easy way", "изи вей", "изивей")
    abank_words = ("a-bank", "a bank", "абанк", "а-банк")
    privat_words = ("privat24", "приват24", "приват 24")
    has_whatsapp = any(word in t for word in whatsapp_words)
    has_ime = any(word in t for word in ime_words)
    has_uklon = "uklon" in t or "уклон" in t
    has_easyway = any(word in t for word in easyway_words)
    has_abank = any(word in t for word in abank_words)
    has_privat = any(word in t for word in privat_words)

    # ---- WhatsApp, only the Android phone application ----
    if has_whatsapp:
        adapter = _phone_adapter("whatsapp")
        if any(word in t for word in ("статус", "состояние", "готов", "подключ")):
            _send_phone_status(api, chat_id, adapter)
            return True
        if any(word in t for word in ("прочитай", "покажи сообщения", "покажи чат", "что в чате", "сообщения")):
            # The wording itself is an explicit request to read the currently
            # visible chat. The adapter masks OTP/card-like sequences.
            result = adapter.read_visible_chat()
            if result.get("status") != "ok":
                api.send_message(chat_id, f"⚠️ WhatsApp: {_phone_error(result)}")
            else:
                messages = result.get("messages") or []
                if not messages:
                    api.send_message(chat_id, "💬 WhatsApp: видимых сообщений не найдено.")
                else:
                    lines = ["💬 <b>WhatsApp · видимая часть текущего чата</b>"]
                    lines.extend(f"• {_esc_tg(item)}" for item in messages[-8:])
                    lines.append("\n<i>Коды и номера карт автоматически скрыты.</i>")
                    api.send_message(chat_id, "\n".join(lines)[:3900])
            return True
        # A draft is always inserted first and then needs a second confirmation
        # to press the actual send control.
        draft_match = re.search(
            r"(?:whatsapp|ватсап|ватс\s*апп|вотсап|watsapp)\s+"
            r"(?:черновик|подготовь\s+ответ|напиши|ответь)\s*[:—–-]\s*(.+)$",
            raw, re.IGNORECASE,
        )
        if not draft_match:
            draft_match = re.search(
                r"^(?:черновик|подготовь\s+ответ)\s+(?:в\s+)?"
                r"(?:whatsapp|ватсап|ватс\s*апп|вотсап|watsapp)\s*[:—–-]\s*(.+)$",
                raw, re.IGNORECASE,
            )
        if draft_match:
            body = draft_match.group(1).strip()
            if not body:
                api.send_message(chat_id, "✍️ Формат: «WhatsApp черновик: текст ответа»")
                return True
            _pending_confirm[chat_id] = {"kind": "whatsapp_draft", "data": {"text": body}}
            api.send_message(chat_id,
                             f"✍️ Вставить черновик в <b>текущий открытый чат WhatsApp</b>?\n"
                             f"Текст: «{_esc_tg(body[:300])}»\n\n"
                             "После вставки будет отдельное подтверждение отправки. «да» / «нет»")
            return True
        chat_match = re.search(
            r"(?:открой|найди)\s+(?:чат\s+)?(?:в\s+)?"
            r"(?:whatsapp|ватсап|ватс\s*апп|вотсап|watsapp)\s*(?:чат)?\s*[:—–-]?\s*(.+)$",
            raw, re.IGNORECASE,
        )
        if not chat_match:
            chat_match = re.search(
                r"(?:whatsapp|ватсап|ватс\s*апп|вотсап|watsapp)\s+"
                r"(?:открой|найди)\s+чат\s*[:—–-]?\s*(.+)$",
                raw, re.IGNORECASE,
            )
        if chat_match:
            contact = chat_match.group(1).strip(" .,:;—–-")
            if not contact:
                api.send_message(chat_id, "💬 Формат: «открой чат WhatsApp: Имя»")
                return True
            _pending_confirm[chat_id] = {"kind": "whatsapp_open_chat", "data": {"contact": contact}}
            api.send_message(chat_id,
                             f"💬 Открыть чат WhatsApp «<b>{_esc_tg(contact[:100])}</b>»?\n"
                             "Это может пометить чат как прочитанный. «да» / «нет»")
            return True
        if any(word in t for word in ("открой", "запусти")):
            _pending_confirm[chat_id] = {"kind": "phone_open_adapter", "data": {"app": "whatsapp"}}
            api.send_message(chat_id, "📱 Открыть WhatsApp на телефоне? «да» / «нет»")
            return True
        api.send_message(chat_id,
                         "💬 <b>WhatsApp на телефоне</b>\n"
                         "• «WhatsApp статус»\n"
                         "• «открой чат WhatsApp: Имя»\n"
                         "• «WhatsApp черновик: текст» — затем отдельное подтверждение отправки\n"
                         "• «прочитай WhatsApp» — только видимый текущий чат")
        return True

    # ---- iMe: draft only in a chat opened manually on the phone ----
    if has_ime:
        adapter = _phone_adapter("ime")
        if any(word in t for word in ("статус", "состояние", "готов", "подключ")):
            _send_phone_status(api, chat_id, adapter)
            return True
        draft_match = re.search(r"(?:ime|i\.me|айми|име\s+мессенджер)\s+(?:черновик|напиши|ответь)\s*[:—–-]\s*(.+)$", raw, re.IGNORECASE)
        if draft_match:
            body = draft_match.group(1).strip()
            _pending_confirm[chat_id] = {"kind": "ime_draft", "data": {"text": body}}
            api.send_message(chat_id,
                             f"✍️ Вставить черновик в текущий открытый чат iMe?\n«{_esc_tg(body[:300])}»\n\n"
                             "Отправка будет подтверждаться отдельно. «да» / «нет»")
            return True
        chat_match = re.search(
            r"(?:открой|найди)\s+(?:чат\s+)?(?:в\s+)?"
            r"(?:ime|i\.me|айми|име\s+мессенджер)\s*(?:чат)?\s*[:—–-]?\s*(.+)$",
            raw, re.IGNORECASE,
        )
        if not chat_match:
            chat_match = re.search(
                r"(?:ime|i\.me|айми|име\s+мессенджер)\s+"
                r"(?:открой|найди)\s+чат\s*[:—–-]?\s*(.+)$",
                raw, re.IGNORECASE,
            )
        if chat_match:
            contact = chat_match.group(1).strip(" .,:;—–-")
            if not contact:
                api.send_message(chat_id, "💬 Формат: «открой чат iMe: Имя»")
                return True
            _pending_confirm[chat_id] = {"kind": "ime_open_chat", "data": {"contact": contact}}
            api.send_message(chat_id,
                             f"💬 Открыть чат iMe «<b>{_esc_tg(contact[:100])}</b>»?\n"
                             "Это может пометить чат как прочитанный. «да» / «нет»")
            return True
        if any(word in t for word in ("открой", "запусти")):
            _pending_confirm[chat_id] = {"kind": "phone_open_adapter", "data": {"app": "ime"}}
            api.send_message(chat_id, "📱 Открыть iMe Messenger на телефоне? «да» / «нет»")
            return True
        api.send_message(chat_id,
                         "💬 <b>iMe Messenger</b>\n"
                         "• «iMe статус»\n• «открой чат iMe: Имя»\n"
                         "• «iMe черновик: текст» — отправка только после второго подтверждения")
        return True

    # ---- Uklon: never books/orders a ride automatically ----
    if has_uklon:
        adapter = _phone_adapter("uklon")
        if any(phrase in t for phrase in ("продолжи маршрут", "продолжить маршрут")):
            route = _phone_route_drafts.get(chat_id) or {}
            route_id = str(route.get("route_id") or "")
            field = str(route.get("next_field") or "")
            if not route_id or not _uklon_route_field_allowed(field):
                api.send_message(chat_id, "ℹ️ Сначала создайте черновик: «маршрут Uklon: откуда -> остановка -> куда».")
                return True
            _pending_confirm[chat_id] = {"kind": "uklon_enter_route_query", "data": {"route_id": route_id, "field": field}}
            label = _uklon_route_field_label(field)
            api.send_message(chat_id,
                             f"🚕 Ввести подготовленный поисковый запрос для «{label}» в Uklon?\n"
                             "AIOS не будет выбирать подсказку и не создаст заказ. «да» / «нет»")
            return True
        if any(word in t for word in ("калибр", "проверь интерфейс", "настрой интерфейс")):
            _pending_confirm[chat_id] = {"kind": "phone_calibrate", "data": {"app": "uklon"}}
            api.send_message(chat_id, "🚕 Открыть Uklon Passenger и проверить только элементы маршрута без заказа поездки? «да» / «нет»")
            return True
        if any(word in t for word in ("статус", "состояние", "уведомлен", "готов")):
            _send_phone_status(api, chat_id, adapter)
            return True
        route_request = _parse_uklon_route_request(raw)
        if route_request:
            _pending_confirm[chat_id] = {"kind": "uklon_stage_route", "data": route_request}
            stop_count = len(route_request.get("stops") or [])
            suffix = f" с {stop_count} промежуточными остановками" if stop_count else ""
            api.send_message(chat_id,
                             f"🚕 Открыть Uklon Passenger и подготовить <b>черновик маршрута{suffix}</b>?\n"
                             "Заказ, принятие поездки и любые списания не создаются. «да» / «нет»")
            return True
        if "driver" in t or "водител" in t:
            _pending_confirm[chat_id] = {"kind": "uklon_open_driver", "data": {}}
            api.send_message(chat_id, "🚕 Открыть Uklon Driver на телефоне? «да» / «нет»")
            return True
        if any(word in t for word in ("открой", "запусти")):
            _pending_confirm[chat_id] = {"kind": "phone_open_adapter", "data": {"app": "uklon"}}
            api.send_message(chat_id, "🚕 Открыть Uklon Passenger на телефоне? «да» / «нет»")
            return True
        api.send_message(chat_id,
                         "🚕 Uklon: «Uklon статус», «открой Uklon», "
                         "«маршрут Uklon: откуда -> остановка 1 -> остановка 2 -> куда». "
                         "Заказ поездки всегда остаётся ручным подтверждаемым действием.")
        return True

    # ---- EasyWay: package com.eway, now registered as installed ----
    if has_easyway:
        adapter = _phone_adapter("easyway")
        if any(word in t for word in ("калибр", "проверь интерфейс", "настрой интерфейс")):
            _pending_confirm[chat_id] = {"kind": "phone_calibrate", "data": {"app": "easyway"}}
            api.send_message(chat_id, "🚌 Открыть EasyWay и проверить только элемент поиска маршрута без запроса геолокации? «да» / «нет»")
            return True
        if any(word in t for word in ("статус", "состояние", "готов", "подключ")):
            _send_phone_status(api, chat_id, adapter)
            return True
        route_match = re.search(r"(?:маршрут|остановк\w*|транспорт)\s+(?:easyway|easy\s+way|изи\s*вей|изивей)\s*[:—–-]\s*(.+)$", raw, re.IGNORECASE)
        if route_match:
            destination = route_match.group(1).strip()
            _pending_confirm[chat_id] = {"kind": "easyway_stage_route", "data": {"destination": destination}}
            api.send_message(chat_id,
                             "🚌 Открыть EasyWay и подготовить приватный черновик маршрута?\n"
                             "Геолокация не включается и не отслеживается в фоне. «да» / «нет»")
            return True
        if any(word in t for word in ("открой", "запусти")):
            _pending_confirm[chat_id] = {"kind": "phone_open_adapter", "data": {"app": "easyway"}}
            api.send_message(chat_id, "🚌 Открыть EasyWay на телефоне? «да» / «нет»")
            return True
        api.send_message(chat_id, "🚌 EasyWay подключён как <code>com.eway</code>. Команды: «EasyWay статус», «открой EasyWay», «маршрут EasyWay: остановка или адрес».")
        return True

    # ---- Financial applications: monitoring/status/open only ----
    if has_abank or has_privat:
        app = "abank" if has_abank else "privat24"
        adapter = _phone_adapter(app)
        if any(word in t for word in ("статус", "состояние", "уведомлен", "готов", "подключ")):
            _send_phone_status(api, chat_id, adapter)
            api.send_message(chat_id, "🔒 Банковый режим: только мониторинг уведомлений и подтверждаемое открытие. Платежи, OTP, карты, биометрия и переводы не автоматизируются.")
            return True
        if any(word in t for word in ("открой", "запусти")):
            _pending_confirm[chat_id] = {"kind": "phone_open_adapter", "data": {"app": app}}
            api.send_message(chat_id, f"🏦 Открыть <b>{_esc_tg(adapter.title)}</b> на телефоне? «да» / «нет»")
            return True
        api.send_message(chat_id, f"🏦 {adapter.title}: «{adapter.title} статус» или «открой {adapter.title}». Финансовые операции отключены.")
        return True

    return False


def _cancel_phone_pending(api, chat_id: int, kind: str, data: dict) -> bool:
    if kind not in ("whatsapp_send_draft", "ime_send_draft"):
        return False
    try:
        app = "whatsapp" if kind == "whatsapp_send_draft" else "ime"
        adapter = _phone_adapter(app)
        adapter.cancel_draft(str(data.get("draft_id") or ""))
    except Exception:
        pass
    api.send_message(chat_id, "🚫 Отправка отменена. Текст на экране телефона не удалялся автоматически.")
    return True


def _confirm_phone_pending(api, chat_id: int, kind: str, data: dict) -> bool:
    """Perform one already-confirmed app step; return True when handled."""
    try:
        if kind == "bank_task_review":
            from aios_core.android_bank_monitor import AndroidBankMonitor
            result = AndroidBankMonitor(PROJECT_ROOT).review_task(str(data.get("task_id") or ""))
            if result.get("status") in ("reviewed", "already_reviewed"):
                api.send_message(chat_id, "✅ Локальная банковская задача отмечена обработанной. Финансовых действий не выполнялось.")
            else:
                api.send_message(chat_id, "⚠️ Не удалось обновить банковскую задачу.")
            return True
        if kind == "phone_crm_task_draft":
            app = str(data.get("app") or "")
            adapter = _phone_adapter(app)
            if not adapter:
                api.send_message(chat_id, "⚠️ Неизвестный мессенджер для CRM-задачи.")
                return True
            opened = adapter.open_chat(str(data.get("contact") or ""), confirm=True)
            if opened.get("status") != "opened":
                api.send_message(chat_id, f"⚠️ {_esc_tg(adapter.title)}: {_phone_error(opened)}")
                return True
            drafted = adapter.prepare_draft(str(data.get("text") or ""), confirm=True)
            if drafted.get("status") != "draft_ready":
                api.send_message(chat_id, f"⚠️ Черновик не подготовлен: {_phone_error(drafted)}")
                return True
            send_kind = "ime_send_draft" if app == "ime" else "whatsapp_send_draft"
            _pending_confirm[chat_id] = {"kind": send_kind, "data": {"draft_id": drafted.get("draft_id")}}
            api.send_message(chat_id,
                             "✅ Черновик из CRM follow-up задачи вставлен и проверен. Отправить его сейчас? Это отдельное действие. «да» / «нет»")
            return True
        if kind == "phone_crm_task_complete":
            result = _phone_lead_queue().complete_crm_task(str(data.get("task_id") or ""))
            if result.get("status") in ("completed", "already_completed"):
                api.send_message(chat_id, "✅ Локальная CRM follow-up задача закрыта. Сообщения и клиенты не изменялись.")
            else:
                api.send_message(chat_id, "⚠️ Не удалось закрыть CRM follow-up задачу.")
            return True
        if kind == "phone_lead_promote":
            result = _phone_lead_queue().promote_to_crm_task(str(data.get("lead_id") or ""))
            if result.get("status") in ("crm_task_created", "already_promoted"):
                api.send_message(chat_id,
                                 "✅ Локальная CRM-задача создана. Откройте нужный чат вручную и используйте подтверждаемый черновик ответа. Клиент и сообщение не создавались автоматически.")
            else:
                api.send_message(chat_id, "⚠️ Не удалось создать CRM-задачу для лида.")
            return True
        if kind == "phone_calibrate":
            adapter = _phone_adapter(str(data.get("app") or ""))
            if not adapter:
                api.send_message(chat_id, "⚠️ Неизвестное приложение телефона.")
                return True
            result = adapter.calibrate(confirm=True)
            if result.get("status") == "calibrated":
                selectors = result.get("selectors") or {}
                ready = bool(selectors) and all(bool(value) for value in selectors.values())
                api.send_message(chat_id,
                                 f"✅ Интерфейс <b>{_esc_tg(adapter.title)}</b> проверен: "
                                 f"{'маршрутные элементы найдены' if ready else 'элементы маршрута не найдены; ничего не вводилось'}.")
            else:
                api.send_message(chat_id, f"⚠️ {_esc_tg(adapter.title)}: {_phone_error(result)}")
            return True
        if kind == "phone_open_adapter":
            adapter = _phone_adapter(str(data.get("app") or ""))
            if not adapter:
                api.send_message(chat_id, "⚠️ Неизвестное приложение телефона.")
                return True
            result = adapter.open(confirm=True)
            if result.get("status") == "ok":
                api.send_message(chat_id, f"✅ На телефоне открыт <b>{_esc_tg(adapter.title)}</b>.")
            else:
                api.send_message(chat_id, f"⚠️ {_esc_tg(adapter.title)}: {_phone_error(result)}")
            return True
        if kind == "whatsapp_open_chat":
            adapter = _phone_adapter("whatsapp")
            result = adapter.open_chat(str(data.get("contact") or ""), confirm=True)
            if result.get("status") == "opened":
                api.send_message(chat_id, "✅ Чат WhatsApp открыт. Автоматическая отправка выключена.")
            else:
                api.send_message(chat_id, f"⚠️ WhatsApp: {_phone_error(result)}")
            return True
        if kind == "ime_open_chat":
            adapter = _phone_adapter("ime")
            result = adapter.open_chat(str(data.get("contact") or ""), confirm=True)
            if result.get("status") == "opened":
                api.send_message(chat_id, "✅ Чат iMe открыт. Автоматическая отправка выключена.")
            else:
                api.send_message(chat_id, f"⚠️ iMe: {_phone_error(result)}")
            return True
        if kind in ("whatsapp_draft", "ime_draft"):
            app = "whatsapp" if kind == "whatsapp_draft" else "ime"
            adapter = _phone_adapter(app)
            result = adapter.prepare_draft(str(data.get("text") or ""), confirm=True)
            if result.get("status") != "draft_ready":
                api.send_message(chat_id, f"⚠️ {_esc_tg(adapter.title)}: {_phone_error(result)}")
                return True
            send_kind = "whatsapp_send_draft" if app == "whatsapp" else "ime_send_draft"
            _pending_confirm[chat_id] = {"kind": send_kind, "data": {"draft_id": result.get("draft_id")}}
            api.send_message(chat_id,
                             "✍️ Черновик вставлен и проверен в поле ввода телефона.\n"
                             "<b>Отправить его сейчас?</b> Это отдельное действие. «да» / «нет»")
            return True
        if kind in ("whatsapp_send_draft", "ime_send_draft"):
            app = "whatsapp" if kind == "whatsapp_send_draft" else "ime"
            adapter = _phone_adapter(app)
            result = adapter.send_draft(str(data.get("draft_id") or ""), confirm=True)
            if result.get("status") == "send_tapped":
                api.send_message(chat_id,
                                 "✅ Нажатие «Отправить» выполнено на телефоне. Это не является гарантией доставки — проверьте статус в приложении.")
            else:
                api.send_message(chat_id, f"⚠️ Отправка заблокирована: {_phone_error(result)}")
            return True
        if kind == "uklon_open_driver":
            adapter = _phone_adapter("uklon")
            result = adapter.open_driver(confirm=True)
            if result.get("status") == "ok":
                api.send_message(chat_id, "✅ На телефоне открыт Uklon Driver.")
            else:
                api.send_message(chat_id, f"⚠️ Uklon Driver: {_phone_error(result)}")
            return True
        if kind == "uklon_stage_route":
            adapter = _phone_adapter("uklon")
            pickup = str(data.get("pickup") or "")
            stops = [str(value or "") for value in (data.get("stops") or []) if str(value or "").strip()]
            stage_kwargs = {"confirm": True}
            if stops:
                stage_kwargs["stops"] = stops
            result = adapter.stage_route(pickup, str(data.get("destination") or ""), **stage_kwargs)
            if result.get("status") == "route_staged":
                controls = result.get("controls") or {}
                ready = bool(controls) and all(bool(value) for value in controls.values())
                if ready:
                    field = "pickup" if pickup.strip() else ("stop_1" if stops else "destination")
                    _phone_route_drafts[chat_id] = {
                        "route_id": result.get("route_id"), "next_field": field, "stops": stops,
                    }
                    _pending_confirm[chat_id] = {"kind": "uklon_enter_route_query", "data": {"route_id": result.get("route_id"), "field": field}}
                    label = _uklon_route_field_label(field)
                    api.send_message(chat_id,
                                     f"🚕 Черновик маршрута готов. Ввести поисковый запрос для «{label}»?\n"
                                     "Это только ввод текста: подсказка и заказ не выбираются. «да» / «нет»")
                else:
                    api.send_message(chat_id, "🚕 Черновик Uklon сохранён, но элементы адресов не подтверждены. Заказ поездки <b>не создан</b>.")
            else:
                api.send_message(chat_id, f"⚠️ Uklon: {_phone_error(result)}")
            return True
        if kind == "uklon_enter_route_query":
            adapter = _phone_adapter("uklon")
            field = str(data.get("field") or "")
            result = adapter.prepare_address_query(str(data.get("route_id") or ""), field, confirm=True)
            if result.get("status") == "query_entered":
                route = _phone_route_drafts.setdefault(chat_id, {"route_id": data.get("route_id"), "stops": []})
                next_field = _uklon_next_route_field(field, route)
                route["next_field"] = next_field
                if next_field:
                    api.send_message(chat_id,
                                     f"✅ Запрос для {_uklon_route_field_label(field)} введён. Выберите подсказку <b>вручную на телефоне</b>, затем напишите «продолжи маршрут Uklon» для следующего поля ({_uklon_route_field_label(next_field)}). Заказ не создавался.")
                else:
                    _phone_route_drafts.pop(chat_id, None)
                    api.send_message(chat_id,
                                     f"✅ Запрос для {_uklon_route_field_label(field)} введён. Выберите подсказку <b>вручную на телефоне</b>; заказ поездки не создавался.")
            else:
                api.send_message(chat_id, f"⚠️ Uklon: {_phone_error(result)}")
            return True
        if kind == "easyway_stage_route":
            adapter = _phone_adapter("easyway")
            result = adapter.stage_route(str(data.get("destination") or ""), confirm=True)
            if result.get("status") == "route_staged":
                controls = result.get("controls") or {}
                ready = bool(controls) and all(bool(value) for value in controls.values())
                if ready:
                    _pending_confirm[chat_id] = {"kind": "easyway_enter_route_query", "data": {"route_id": result.get("route_id")}}
                    api.send_message(chat_id,
                                     "🚌 Черновик маршрута готов. Ввести поисковый запрос в EasyWay?\n"
                                     "Маршрут и геолокация не будут выбраны автоматически. «да» / «нет»")
                else:
                    api.send_message(chat_id, "🚌 Черновик EasyWay сохранён, но поле маршрута не подтверждено. Геолокация не отслеживается в фоне.")
            else:
                api.send_message(chat_id, f"⚠️ EasyWay: {_phone_error(result)}")
            return True
        if kind == "easyway_enter_route_query":
            adapter = _phone_adapter("easyway")
            result = adapter.prepare_destination_query(str(data.get("route_id") or ""), confirm=True)
            if result.get("status") == "query_entered":
                api.send_message(chat_id,
                                 "✅ Поисковый запрос введён в EasyWay. Выберите остановку или маршрут <b>вручную на телефоне</b>; геолокация не запрашивалась.")
            else:
                api.send_message(chat_id, f"⚠️ EasyWay: {_phone_error(result)}")
            return True
    except Exception as exc:
        api.send_message(chat_id, f"⚠️ Ошибка сценария телефона: {_esc_tg(str(exc))[:220]}")
        return True
    return False


def _handle_android_gateway_intent(api, chat_id: int, text: str) -> bool:
    """Детерминированные безопасные команды реального Android-адаптера."""
    raw = str(text or "").strip()
    t = " ".join(raw.casefold().split())
    phone_words = ("телефон", "android", "андроид", "смартфон")
    if not any(word in t for word in phone_words):
        return False
    if any(phrase in t for phrase in ("статус телефона", "телефон статус", "android статус", "статус android", "состояние телефона")):
        data = _android_gateway_run(["status"])
        if data.get("status") == "ok":
            api.send_message(chat_id,
                             "📱 <b>Android Device Adapter</b>\n"
                             f"Статус: <b>{'подключён' if data.get('connected') else 'офлайн'}</b>\n"
                             f"Устройство: {_esc_tg(data.get('name') or data.get('model') or '—')}\n"
                             f"Android: {data.get('android') or '—'} · заряд: {data.get('battery', '—')}%\n"
                             f"Экран: {_esc_tg(data.get('screen') or '—')}\n"
                             f"Приложений: {data.get('packages', '—')}")
        else:
            api.send_message(chat_id, f"⚠️ Android gateway: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    if any(phrase in t for phrase in ("управление приложениями телефона", "доступность телефона", "accessibility телефона")):
        data = _android_gateway_run(["accessibility"])
        if data.get("status") == "ok":
            api.send_message(chat_id, "🧩 Управление интерфейсом приложений: " + ("<b>разрешено</b>" if data.get("enabled") else "<b>не разрешено</b>"))
        else:
            api.send_message(chat_id, f"⚠️ Accessibility недоступен: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    if any(phrase in t for phrase in ("уведомления телефона", "уведомления android", "уведомления андроид")):
        data = _android_gateway_run(["notifications"])
        notices = data.get("notifications") or []
        if data.get("status") == "ok" and notices:
            lines = ["🔔 <b>Последние уведомления телефона</b>"]
            for notice in notices[-15:]:
                # Even an explicitly requested notification list must not leak
                # OTP/PIN/card-like values from the live Companion stream.
                lines.append(f"• <code>{_esc_tg(str(notice.get('package') or ''))}</code>\n"
                             f"  <b>{_esc_tg(_mask_android_notification(notice.get('title'), 100))}</b>\n"
                             f"  {_esc_tg(_mask_android_notification(notice.get('text'), 180))}")
            api.send_message(chat_id, "\n".join(lines)[:3900])
        elif data.get("status") == "ok":
            api.send_message(chat_id, "🔔 Уведомлений пока нет. Проверьте, что в Companion включён доступ к уведомлениям.")
        else:
            api.send_message(chat_id, f"⚠️ Уведомления недоступны: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    if any(phrase in t for phrase in ("статус камеры телефона", "статус микрофона телефона", "статус камеры и микрофона", "готовность камеры")):
        data = _android_gateway_run(["capture-status"])
        if data.get("status") == "ok":
            camera = bool(data.get("camera_permission"))
            microphone = bool(data.get("microphone_permission"))
            background = bool(data.get("background_capture"))
            api.send_message(chat_id,
                             "📷 <b>Камера и микрофон телефона</b>\n"
                             f"Камера: {'✅ разрешена' if camera else '⚪ не разрешена'}\n"
                             f"Микрофон: {'✅ разрешён' if microphone else '⚪ не разрешён'}\n"
                             f"Фоновый захват: {'⚠️ включён' if background else '✅ выключен'}\n"
                             "Фото и аудио не записываются этим статусом.")
        else:
            api.send_message(chat_id, f"⚠️ Статус камеры/микрофона недоступен: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    if any(phrase in t for phrase in ("статус геолокации телефона", "готовность геолокации", "геолокация доступна")):
        data = _android_gateway_run(["location-status"])
        if data.get("status") == "ok":
            permission = bool(data.get("permission"))
            ready = bool(data.get("ready"))
            gps = bool(data.get("gps_enabled"))
            network = bool(data.get("network_enabled"))
            api.send_message(chat_id,
                             "📍 <b>Геолокация телефона</b>\n"
                             f"Разрешение: {'✅' if permission else '⚠️'}\n"
                             f"GPS: {'✅ включён' if gps else '⚪ выключен'} · сеть: {'✅ включена' if network else '⚪ выключена'}\n"
                             f"Готовность без запроса координат: {'✅' if ready else '⚠️'}")
        else:
            api.send_message(chat_id, f"⚠️ Статус геолокации недоступен: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    if any(phrase in t for phrase in ("геолокация телефона", "местоположение телефона", "где телефон", "локация телефона")):
        _pending_confirm[chat_id] = {"kind": "android_location", "data": {}}
        api.send_message(chat_id, "📍 Запросить текущую геолокацию телефона?\n\n«да» / «нет»")
        return True
    if any(phrase in t for phrase in ("файлы телефона", "файлы android", "загрузки телефона")):
        data = _android_gateway_run(["files"])
        if data.get("status") == "ok":
            lines = [f"📂 <b>{_esc_tg(data.get('directory') or '')}</b> · {data.get('count', 0)} файлов"]
            lines += [f"• {_esc_tg(name)}" for name in (data.get('files') or [])[:40]]
            api.send_message(chat_id, "\n".join(lines)[:3900])
        else:
            api.send_message(chat_id, f"⚠️ Файлы недоступны: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    m_pull = re.search(r"(?:скачай|загрузи)\s+с\s+(?:телефона|android|андроида)\s*:?\s*(/sdcard/(?:Download|Documents|Pictures|DCIM)/[^\s]+)", raw, re.IGNORECASE)
    if m_pull:
        path = m_pull.group(1)
        _pending_confirm[chat_id] = {"kind": "android_pull_file", "data": {"path": path}}
        api.send_message(chat_id, f"📥 Скачать с телефона <code>{_esc_tg(path)}</code>?\n\n«да» / «нет»")
        return True
    if any(phrase in t for phrase in ("рабочие приложения", "приложения для работы", "профили приложений", "телефон приложения работа")):
        data = _android_gateway_run(["profiles"])
        profiles = data.get("profiles") or []
        if data.get("status") == "ok":
            lines = ["📱 <b>Рабочие приложения телефона</b>"]
            for profile in profiles:
                state = "✅" if profile.get("available") else "➕"
                package = (profile.get("installed") or ["не установлено"])[0]
                sensitive = " · подтверждение обязательно" if profile.get("sensitive") else ""
                lines.append(f"{state} <b>{_esc_tg(profile.get('title'))}</b>\n"
                             f"  <code>{_esc_tg(package)}</code>\n"
                             f"  {_esc_tg(profile.get('mode'))}{sensitive}")
            api.send_message(chat_id, "\n".join(lines)[:3900])
        else:
            api.send_message(chat_id, f"⚠️ Профили недоступны: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    if any(phrase in t for phrase in ("приложения телефона", "список приложений", "приложения android", "андроид приложения")):
        data = _android_gateway_run(["apps"])
        if data.get("status") == "ok":
            apps = data.get("apps") or []
            lines = [f"📱 <b>Приложения Android</b> · всего: {data.get('count', 0)}"]
            lines += [f"• <code>{_esc_tg(app)}</code>" for app in apps[:35]]
            if len(apps) > 35:
                lines.append(f"… показаны первые 35 из {data.get('count', 0)}")
            api.send_message(chat_id, "\n".join(lines)[:3900])
        else:
            api.send_message(chat_id, f"⚠️ Не удалось получить приложения: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    if any(phrase in t for phrase in ("скрин телефона", "скриншот телефона", "снимок телефона", "экран телефона")):
        api.send_message(chat_id, "⏳ Получаю защищённый снимок экрана телефона…")
        data = _android_gateway_run(["screenshot"], timeout=90)
        if data.get("status") == "ok" and data.get("file"):
            api.send_photo(chat_id, data["file"], caption="📱 Снимок Android-экрана")
        else:
            api.send_message(chat_id, f"⚠️ Скриншот недоступен: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    if any(phrase in t for phrase in ("ui телефона", "структура интерфейса телефона", "дамп интерфейса телефона")):
        data = _android_gateway_run(["ui-dump"], timeout=90)
        if data.get("status") == "ok" and data.get("file"):
            api.send_document(chat_id, data["file"], caption="📱 UIAutomator dump Android")
        else:
            api.send_message(chat_id, f"⚠️ UI dump недоступен: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    m_open = re.search(r"(?:открой|запусти)\s+(?:на\s+)?(?:телефоне|android|андроиде)\s*:?\s*([\w.]+)", raw, re.IGNORECASE)
    if m_open:
        package = m_open.group(1).strip()
        _pending_confirm[chat_id] = {"kind": "android_open_app", "data": {"package": package}}
        api.send_message(chat_id, f"📱 Открыть на телефоне <code>{_esc_tg(package)}</code>?\n\n«да» / «нет»")
        return True
    if any(phrase in t for phrase in ("телефон помощь", "android помощь", "помощь с телефоном")):
        api.send_message(chat_id,
                         "📱 <b>Android Adapter</b>\n"
                         "• «статус телефона»\n• «рабочие приложения»\n• «приложения телефона»\n"
                         "• «уведомления телефона»\n• «геолокация телефона»\n"
                         "• «файлы телефона»\n• «скрин телефона»\n• «ui телефона»\n"
                         "• «открой на телефоне com.android.settings»")
        return True
    return False
