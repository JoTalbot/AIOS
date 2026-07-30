#!/usr/bin/env python3
"""Notification Skill v4 — информативные отчёты агента с inline кнопками Отменить/Углубить"""
import json
import os
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

JOURNAL_PATH = Path(os.path.expanduser("~/agents/-Octopus/logs/autonomy_journal.jsonl"))
CHANGES_LOG = Path(os.path.expanduser("~/agents/-Octopus/logs/changes_log.jsonl"))
TG_TOKEN_PATH = Path("/run/octopus/telegram_bot_token")
TG_CHAT_PATH = Path("/run/octopus/telegram_chat_id")
SECRETS_PATH = Path("/etc/octopus/secrets.env")

TASK_NAMES = {
    "health_fix": "🔧 Исправление здоровья системы",
    "cleanup": "🧹 Очистка диска и ресурсов",
    "skill_implement": "🧩 Имплементация нового скилла",
    "skill_audit": "🔍 Аудит скиллов проекта",
    "memory_check": "🧠 Проверка целостности памяти",
    "scale_free": "🖥️ Масштабирование (бесплатные ноды)",
    "experience_learn": "📚 Анализ опыта и обучение",
    "todo_task": "📋 Выполнение задачи из плана",
}

def _get_tg_creds():
    token = chat_id = None
    if TG_TOKEN_PATH.exists():
        token = TG_TOKEN_PATH.read_text().strip()
    if TG_CHAT_PATH.exists():
        chat_id = TG_CHAT_PATH.read_text().strip()
    if not token or not chat_id:
        if SECRETS_PATH.exists():
            for line in SECRETS_PATH.read_text().split("\n"):
                if line.startswith("TELEGRAM_BOT_TOKEN=") and not token:
                    token = line.split("=", 1)[1].strip()
                elif line.startswith("TELEGRAM_CHAT_ID=") and not chat_id:
                    chat_id = line.split("=", 1)[1].strip()
    if not token:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not chat_id:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    return token, chat_id

def _tg_api(method, payload):
    token, chat_id = _get_tg_creds()
    if not token:
        return {"ok": False, "error": "no_token"}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}

def send_project_telegram(token, chat_id, text, reply_markup=None, timeout=15):
    """Централизованный транспорт для проектных Telegram-уведомлений."""
    if not token or not chat_id:
        return {"ok": False, "reason": "bot_not_configured"}
    payload = {"chat_id": chat_id, "text": str(text)[:3900], "disable_web_page_preview": True}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def log_to_journal(message, level="info"):
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "level": level, "message": message}
    with open(JOURNAL_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry

def log_change(change_id, description, details, rollback_cmd=None):
    CHANGES_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "id": change_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "description": description,
        "details": details,
        "rollback_cmd": rollback_cmd,
        "status": "applied",
        "reverted": False
    }
    with open(CHANGES_LOG, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry

def get_recent_changes(limit=5):
    if not CHANGES_LOG.exists():
        return []
    changes = []
    with open(CHANGES_LOG) as f:
        for line in f:
            try:
                changes.append(json.loads(line.strip()))
            except:
                pass
    return changes[-limit:]

def _strip_html(text):
    import re
    return re.sub(r"<[^>]+>", "", text)

def send_telegram(text):
    token, chat_id = _get_tg_creds()
    if not token or not chat_id:
        return {"delivered": False, "reason": "no_tg_creds"}
    if len(text) > 4000:
        text = text[:3997] + "..."
    res = _tg_api("sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
    if not res.get("ok"):
        res = _tg_api("sendMessage", {"chat_id": chat_id, "text": _strip_html(text)[:3997]})
    return res

def notify_agent_report(cycle_id, health_score, health_grade, task_type, task_desc,
                        result_action, success, score_delta, changes=None):
    """Подробный интуитивный отчёт агента на русском с inline-кнопками управления."""
    delta = f"+{score_delta}" if score_delta > 0 else str(score_delta) if score_delta != 0 else "без изменений"
    icon = "✅" if success else "❌"
    task_label = TASK_NAMES.get(task_type, task_type)
    explanations = {
        "health_fix": "проверил слабые места здоровья системы и попытался убрать причину деградации",
        "cleanup": "оценил расход диска/ресурсов и выполнил безопасную очистку без удаления важных данных",
        "skill_implement": "развил скиллы агента: проверил структуру, код, тесты и пригодность к повторному использованию",
        "skill_audit": "проверил набор скиллов, чтобы агент не работал вслепую и не оставлял пустые заглушки",
        "memory_check": "проверил журналы, опыт и компактный контекст, чтобы следующие циклы продолжали работу осмысленно",
        "all_vectors": "обновил общую карту развития, чтобы автономия не зацикливалась на одном пункте",
        "quality_smoke": "выполнил быстрые проверки качества/компиляции и зафиксировал результат",
        "memory_learn": "извлёк полезный опыт из последних действий и подготовил память для следующих шагов",
        "telegram_audit": "проверил Telegram-интерфейс, кнопки и отзывчивость управления",
    }
    human_done = explanations.get(task_type, "выполнил ограниченный безопасный шаг развития проекта и сохранил следы работы в логах")
    if result_action:
        human_done += f". Технически это записано как действие: {result_action}"
    text = (
        f"{icon} <b>Octopus — отчёт автономного ИИ-агента</b>\n\n"
        f"🕐 <b>Цикл:</b> <code>{cycle_id}</code>\n"
        f"🏥 <b>Здоровье:</b> <b>{health_score}/{health_grade}</b> ({delta})\n\n"
        f"📌 <b>Направление работы:</b> {task_label}\n"
        f"📝 <b>Задача:</b> {task_desc}\n\n"
        f"🛠 <b>Что реально сделано:</b> {human_done}.\n\n"
        f"🎯 <b>Результат:</b> {'успешно, можно продолжать развитие' if success else 'есть ошибка, стоит открыть логи и проверить причину'}\n"
        f"📎 <b>Где смотреть детали:</b> <code>~/agents/-Octopus/logs/</code> и <code>~/agents/-Octopus/reports/</code>\n"
    )
    buttons = []
    if changes:
        text += "\n<b>Изменения/артефакты цикла:</b>\n"
        for ch in changes:
            desc = ch.get("description", "?")
            cid = ch.get("id", cycle_id)
            text += f"• <code>{cid}</code> — {desc}\n"
            buttons.append([
                {"text": f"↩️ Отменить: {desc[:24]}", "callback_data": f"agent:rollback:{cid}"},
                {"text": f"📈 Углубить: {desc[:24]}", "callback_data": f"agent:improve:{cid}"}
            ])
    else:
        buttons.append([
            {"text": "📈 Углубить это направление", "callback_data": f"agent:improve:{cycle_id}"}
        ])
    buttons.append([
        {"text": "🔄 Следующий цикл", "callback_data": "agent:cycle"},
        {"text": "🏥 Здоровье", "callback_data": "agent:health"}
    ])
    payload = {
        "chat_id": _get_tg_creds()[1],
        "text": text[:3900],
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": buttons}
    }
    res = _tg_api("sendMessage", payload)
    if not res.get("ok"):
        payload.pop("parse_mode", None)
        payload["text"] = _strip_html(text)[:3900]
        res = _tg_api("sendMessage", payload)
    return res

def notify_critical(message):
    return send_telegram(f"🚨 <b>КРИТИЧЕСКОЕ:</b> {message}")

def notify(message, level="info", channel="both"):
    result = {"timestamp": datetime.now(timezone.utc).isoformat(), "level": level}
    if channel in ("log", "both"):
        log_to_journal(message, level)
        result["logged"] = True
    if channel in ("telegram", "both"):
        result["telegram"] = send_telegram(f"🐙 {message}")
    return result

if __name__ == "__main__":
    import sys
    msg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Test"
    result = notify(msg, channel="both")
    print(json.dumps(result, indent=2, ensure_ascii=False))
