#!/usr/bin/env python3
"""
AIOS Platform Autoreply — автономные ответы в мессенджерах (IG / FB / Viber).

Использует тот же контур автономии, что и OLX. Цикл по расписанию:
  python run_platform_autoreply.py instagram --loop --interval 300
  python run_platform_autoreply.py facebook  --once

Конфиг: data/platform_autoreply.json
  {"enabled": true, "auto_send": true, "max_replies_per_run": 3}
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

PY = "/opt/aios/.venv/bin/python"
CFG_PATH = ROOT / "data" / "platform_autoreply.json"


def _env(key: str) -> str:
    import os
    v = os.environ.get(key, "")
    if v:
        return v
    p = ROOT / ".env"
    if p.exists():
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith(key + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return ""


def _load_cfg(platform: str = "") -> dict:
    """Общий конфиг + безопасное переопределение конкретной платформы.

    Старые IG/FB настройки остаются совместимыми. Для нового Viber можно
    задать ``platforms.viber.auto_send=false`` и сначала получать только
    черновики в Telegram, не рискуя отправить сообщение автоматически.
    """
    default = {"enabled": True, "auto_send": True, "max_replies_per_run": 3}
    try:
        raw = json.loads(CFG_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raw = {}
    except Exception:
        raw = {}
    cfg = {**default, **{k: v for k, v in raw.items() if k != "platforms"}}
    platforms = raw.get("platforms") if isinstance(raw.get("platforms"), dict) else {}
    per_platform = platforms.get(platform) if platform else {}
    if isinstance(per_platform, dict):
        cfg.update(per_platform)
    return cfg


def _tg(token: str, chat_id: int, text: str, reply_markup: dict | None = None) -> None:
    import urllib.request
    import html as _html
    payload = {"chat_id": chat_id, "text": _html.escape(text)[:3800],
               "parse_mode": "HTML", "disable_web_page_preview": True}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60):
        pass


def _queue_viber_draft(contact: str, text: str, source_text: str, token: str, chat_id: str) -> bool:
    """Сохранить Viber-черновик и прислать владельцу кнопки подтверждения."""
    try:
        from viber_drafts import ViberDraftStore
        draft, created = ViberDraftStore(ROOT).enqueue(contact, text, source_text)
    except Exception as exc:
        print(f"  [viber-draft] queue error: {exc}")
        return False
    if not created:
        return False
    if token and chat_id:
        keyboard = {"inline_keyboard": [[
            {"text": "✅ Отправить", "callback_data": f"viber_draft_send_{draft['id']}"},
            {"text": "❌ Отклонить", "callback_data": f"viber_draft_cancel_{draft['id']}"},
        ]]}
        message = (f"💜 Черновик Viber для {contact}:\n«{text[:500]}»\n\n"
                   "Проверьте текст и выберите действие.")
        try:
            _tg(token, int(chat_id), message, keyboard)
        except Exception as exc:
            print(f"  [viber-draft] Telegram error: {exc}")
    return True


def _run_ac(args: list[str], timeout: int = 170) -> dict:
    helper = str(ROOT / "run_account_control.py")
    cmd = [PY, helper] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "timeout (браузер занят)"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}
    out = (r.stdout or "").strip()
    if not out:
        return {"status": "error", "error": (r.stderr or "пустой ответ")[-400:]}
    try:
        start = out.find("{")
        return json.loads(out[start:]) if start >= 0 else {"status": "error", "error": out[-400:]}
    except Exception:
        return {"status": "error", "error": out[-400:]}


# Маппинг платформ на команды run_account_control
_PLATFORM_CMDS = {
    "instagram": {"list": ["instagram", "dm_list", "6"], "reply": "instagram"},
    "facebook": {"list": ["facebook", "messenger_list", "--limit", "6"], "reply": "facebook"},
    "viber": {"list": ["viber", "chats"], "reply": "viber"},
}


def _list_dms(platform: str) -> list[dict]:
    cfg = _PLATFORM_CMDS[platform]
    res = _run_ac(cfg["list"], timeout=170)
    # нормализация: надеемся на поле chats/messages/threads с полями contact/name + last/text
    if isinstance(res, dict):
        for key in ("threads", "chats", "messages", "items", "dialogs"):
            if isinstance(res.get(key), list):
                return res[key]
    return []


def _read_dm(platform: str, contact: str) -> list[dict]:
    if platform == "instagram":
        return _run_ac(["instagram", "dm_read", contact, "10"], timeout=170).get("messages", [])
    if platform == "facebook":
        return _run_ac(["facebook", "messenger_read", contact, "10"], timeout=170).get("messages", [])
    if platform == "viber":
        return _run_ac(["viber", "read", contact, "10"], timeout=120).get("messages", [])
    return []


def _contact_allowed(platform: str, contact: str, cfg: dict) -> bool:
    """Viber drafts are opt-in per chat to avoid touching personal dialogs."""
    if platform != "viber":
        return True
    allowed = cfg.get("allowed_chats", [])
    if allowed == "*":
        return True
    if not isinstance(allowed, list):
        return False
    normalized = {str(value).strip().casefold() for value in allowed}
    return "*" in normalized or str(contact).strip().casefold() in normalized


def _reply(platform: str, contact: str, text: str) -> dict:
    if platform == "instagram":
        return _run_ac(["instagram", "dm_send", contact, text, "--confirm"], timeout=170)
    if platform == "facebook":
        return _run_ac(["facebook", "messenger_send", contact, text, "--confirm"], timeout=170)
    if platform == "viber":
        return _run_ac(["viber", "send", contact, text, "--confirm"], timeout=120)
    return {"status": "error", "error": "нет платформы"}


def run_cycle(platform: str) -> dict:
    from aios_core.autonomy import AutonomyCore
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat_id = _env("TELEGRAM_CHAT_ID")
    cfg = _load_cfg(platform)
    if not cfg.get("enabled"):
        return {"ok": False, "reason": "disabled"}
    if platform not in _PLATFORM_CMDS:
        return {"ok": False, "reason": f"platform {platform} unsupported"}

    core = AutonomyCore()
    if not core.policy.enabled:
        return {"ok": False, "reason": "autonomy disabled"}

    dms = _list_dms(platform)
    replied = 0
    drafted = 0
    handled = 0
    max_r = int(cfg.get("max_replies_per_run", 3))
    summary = []

    for dm in dms[:10]:
        if handled >= max_r:
            break
        contact = str(dm.get("name") or dm.get("contact") or dm.get("id") or "").strip()
        if not contact or not _contact_allowed(platform, contact, cfg):
            continue
        # Viber chats() намеренно не притворяется, что знает preview/unread.
        # Для Viber получаем последний входящий текст только при явном цикле.
        last = str(dm.get("text") or dm.get("last_message") or dm.get("last") or "").strip()
        msgs = []
        if platform == "viber":
            msgs = _read_dm(platform, contact)
            last_theirs = next((m.get("text", "") for m in reversed(msgs)
                                if not m.get("mine") and m.get("text")), "")
            last = str(last_theirs or "").strip()
        else:
            if not last:
                continue
            msgs = _read_dm(platform, contact)
            # Сохраняем прежний порядок для уже работающих IG/FB контуров.
            last_theirs = next((m.get("text", "") for m in msgs
                                if not m.get("mine") and m.get("text")), "")
        if not last_theirs:
            continue
        sess = core.state.get(platform, contact)
        if sess.last_seen_msg == f"{contact}:{last}":
            continue
        outcome = core.process_customer(platform, contact, last_theirs,
                                        msg_id=f"{contact}:{last}", extra={"item": None, "history": msgs})
        if outcome.get("mode") == "action" and outcome.get("text"):
            if cfg.get("auto_send", True):
                res = _reply(platform, contact, outcome["text"])
                if res.get("status") == "sent" or res.get("status") == "ok":
                    replied += 1
                    handled += 1
                    summary.append(f"✅ {platform}/{contact}: {outcome['text'][:50]}")
                else:
                    summary.append(f"⚠️ {platform}/{contact}: ответ не отправлен")
            else:
                if platform == "viber":
                    created = _queue_viber_draft(contact, outcome["text"], last_theirs, token, chat_id)
                    if created:
                        drafted += 1
                        handled += 1
                        summary.append(f"💜 viber/{contact}: черновик ожидает подтверждения")
                else:
                    handled += 1
                    summary.append(f"💬 {platform}/{contact}: черновик «{outcome['text'][:110]}»")
        elif outcome.get("mode") in ("escalate", "manual", "blocked") and outcome.get("text"):
            summary.append(f"🔎 {platform}/{contact}: {outcome['decision']} — {outcome['text'][:50]}")

    if summary and token and chat_id:
        try:
            _tg(token, int(chat_id), f"📊 <b>Цикл {platform}</b>\n" + "\n".join(summary[:10]))
        except Exception:
            pass
    return {"ok": True, "platform": platform, "replied": replied, "drafted": drafted,
            "summary": summary}


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: run_platform_autoreply.py <platform> [--once|--loop [--interval N]]")
        return 1
    platform = sys.argv[1]
    args = sys.argv[2:]
    if "--once" in args:
        r = run_cycle(platform)
        print(json.dumps(r, ensure_ascii=False))
        return 0
    if "--loop" in args:
        interval = 300
        if "--interval" in args:
            i = args.index("--interval")
            if i + 1 < len(args):
                try:
                    interval = int(args[i + 1])
                except ValueError:
                    pass
        print(f"🔁 {platform}-автоответ: loop каждые {interval}с (Ctrl+C для выхода)")
        while True:
            try:
                run_cycle(platform)
            except Exception as e:
                print(f"  [{platform}-loop] error: {e}")
            time.sleep(interval)
        return 0
    return run_cycle(platform)


if __name__ == "__main__":
    sys.exit(main())
