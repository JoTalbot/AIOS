#!/usr/bin/env python3
"""
AIOS OLX Autoreply — автономные ответы покупателям в OLX-чате.

Использует единый контур автономии (aios_core.autonomy.AutonomyCore):
  вход покупателя -> intent -> LLM-предложение -> guardrails -> исполнение.

Режимы (data/olx_autoreply.json):
  enabled    : bool  — общий вкл/выкл
  auto_send  : bool  — если true, разрешённые ответы шлются в OLX-чат авто;
                       если false — предлагаемый ответ отправляется владельцу на подтверждение.
  max_replies_per_run : int — лимит автоответов за один цикл.

Команды в боте: «включи автоответ OLX» / «выключи автоответ OLX».
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

CFG = ROOT / "data" / "olx_autoreply.json"
PY = "/opt/aios/.venv/bin/python"


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


def _load_cfg() -> dict:
    default = {"enabled": False, "auto_send": True, "max_replies_per_run": 3}
    try:
        cfg = json.loads(CFG.read_text(encoding="utf-8"))
        cfg = {**default, **cfg}
        return cfg
    except Exception:
        return default


def _save_cfg(cfg: dict) -> None:
    CFG.parent.mkdir(parents=True, exist_ok=True)
    CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_ac(args: list[str], timeout: int = 170) -> dict:
    """Запустить run_account_control.py для OLX-чата (браузер → xvfb)."""
    helper = str(ROOT / "run_account_control.py")
    cmd = ["xvfb-run", "-a", "-s", "-screen 0 1440x900x24", PY, helper] + args
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


def _tg(token: str, chat_id: int, text: str) -> None:
    import urllib.request
    import html as _html
    payload = {"chat_id": chat_id, "text": _html.escape(text)[:3800],
               "parse_mode": "HTML", "disable_web_page_preview": True}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60):
        pass


def _detect_item(text: str) -> str | None:
    """Сопоставить текст сообщения с товарами из склада (для ценового пола)."""
    try:
        import run_inventory
        items = run_inventory._load()
    except Exception:
        items = []
    t = (text or "").lower()
    for it in items:
        name = (it.get("name") or "").strip()
        if not name:
            continue
        if name.lower() in t or t in name.lower():
            return name
    # также ищем по известным полам
    try:
        import json
        floors = json.loads((ROOT / "data" / "price_floors.json").read_text(encoding="utf-8"))
        for key in floors.get("items", {}):
            if key in t:
                return key
    except Exception:
        pass
    return None


def get_olx_threads() -> list[dict]:
    """Список переписок OLX-чата: [{contact, text, unread}]."""
    res = _run_ac(["olx", "chat", "list", "20"], timeout=170)
    threads = res.get("threads", []) or []
    return threads


def read_olx(contact: str) -> dict:
    return _run_ac(["olx", "chat", "read", contact, "15"], timeout=170)


def reply_olx(contact: str, text: str) -> dict:
    return _run_ac(["olx", "chat", "reply", contact, text, "--confirm"], timeout=170)


def main() -> int:
    from aios_core.autonomy import AutonomyCore

    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat_id = _env("TELEGRAM_CHAT_ID")
    cfg = _load_cfg()
    if not cfg.get("enabled"):
        print("Автоответ OLX выключен")
        return 0

    core = AutonomyCore()
    if not core.policy.enabled:
        print("Автономия выключена в data/autonomy_policy.json")
        return 0

    threads = get_olx_threads()
    if not threads:
        print("OLX-чат: переписок нет")
        return 0

    max_r = int(cfg.get("max_replies_per_run", 3))
    replied = 0
    actions_summary = []

    for th in threads[:20]:
        if replied >= max_r:
            break
        contact = (th.get("name") or "").strip()
        last = (th.get("text") or "").strip()
        if not contact or not last:
            continue

        # дедупликация через сессию автономии
        sess = core.state.get("olx", contact)
        if sess.last_seen_msg == f"{contact}:{last}":
            continue  # уже отвечали

        # прочитать переписку, чтобы понять контекст
        conv = read_olx(contact)
        msgs = conv.get("messages", []) or []

        # последнее сообщение НЕ от нас — надо ответить
        last_theirs = None
        for m in msgs:
            if not m.get("mine"):
                last_theirs = m.get("text", "")
                break
        if not last_theirs:
            continue

        detected = _detect_item(last_theirs)
        outcome = core.process_customer(
            "olx", contact, last_theirs, msg_id=f"{contact}:{last}",
            extra={"item": detected, "ad_price": None})

        # действие — автоответ
        if outcome.get("mode") == "action" and outcome.get("text"):
            reply_text = outcome["text"]
            auto = cfg.get("auto_send", True)
            if auto:
                res = reply_olx(contact, reply_text)
                if res.get("status") == "ok":
                    replied += 1
                    actions_summary.append(f"✅ {contact}: {reply_text[:60]}")
                else:
                    # не отправилось — уведомить владельца
                    _tg(token, int(chat_id),
                        f"⚠️ Автоответ OLX не отправился {contact}: {res.get('error','?')}")
            else:
                _tg(token, int(chat_id),
                    f"💬 <b>Предлагаемый ответ для {contact}:</b>\n{reply_text[:600]}\n\n"
                    f"Отправить: «ответь в олх: {contact} | текст» или включи auto_send.")
        elif outcome.get("mode") in ("escalate", "manual", "blocked"):
            # эскалация уже уведомила владельца
            if outcome.get("text"):
                actions_summary.append(f"🔎 {contact}: {outcome['decision']} — {outcome['text'][:60]}")

    if actions_summary:
        _tg(token, int(chat_id), "📊 <b>Цикл автоответа OLX</b>\n" + "\n".join(actions_summary[:10]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
