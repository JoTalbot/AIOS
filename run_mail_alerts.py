#!/usr/bin/env python3
"""
AIOS Mail Alerts — следит за новыми «важными» письмами (по ключевым словам
в теме/отправителе) и шлёт уведомление в Telegram. Запускается по таймеру
(например, каждые 15 минут); state-файл предотвращает повторы.

Настройка ключевых слов — переменная MAIL_ALERT_KEYWORDS в .env
(через запятую) или константа ниже.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

STATE = ROOT / "data" / "mail_alerts_seen.json"

# Ключевые слова: письмо считается «важным», если они есть в теме или отправителе
DEFAULT_KEYWORDS = [
    "срочно", "важно", "важное", "invoice", "инвойс", "счёт", "счет",
    "alert", "security", "security@", "взлом", "подтверждение", "код",
    "оплата", "заказ", "договор", "контракт", "github", "pull request",
    "письмо", "уведомлени",
]


def _env(key: str) -> str:
    v = __import__("os").environ.get(key, "")
    if v:
        return v
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _keywords() -> list[str]:
    kw = _env("MAIL_ALERT_KEYWORDS")
    if kw:
        return [k.strip().lower() for k in kw.split(",") if k.strip()]
    return DEFAULT_KEYWORDS


def _load_state() -> set[str]:
    try:
        return set(json.loads(STATE.read_text()))
    except Exception:
        return set()


def _save_state(seen: set[str]) -> None:
    seen = set(list(seen)[-800:])
    STATE.write_text(json.dumps(list(seen), ensure_ascii=False))


def _tg(token: str, chat_id: int, text: str) -> None:
    payload = {"chat_id": chat_id, "text": text[:3900],
               "parse_mode": "HTML", "disable_web_page_preview": True}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60):
        pass


def main() -> int:
    import run_account_control as rac

    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat = _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("Нет токена/чата в .env"); return 1

    keywords = _keywords()
    # ищем свежие непрочитанные
    g = rac.gmail_list(25, unread_only=True)
    if g.get("status") != "ok":
        print("Ошибка IMAP:", g.get("error")); return 1

    seen = _load_state()
    alerts = []
    for e in g.get("emails", []):
        eid = e.get("id", "")
        if eid in seen:
            continue
        subj = (e.get("subject") or "").lower()
        frm = (e.get("from") or "").lower()
        if any(k in subj or k in frm for k in keywords):
            seen.add(eid)
            alerts.append(e)

    if not alerts:
        _save_state(seen)
        print("Важных новых писем нет.")
        return 0

    for e in alerts:
        import html as _html
        text = (f"🚨 <b>Важное письмо</b>\n"
                f"📧 <b>{_html.escape(e.get('subject') or '?')}</b>\n"
                f"✉️ {_html.escape(e.get('from') or '?')}\n"
                f"🕐 {_html.escape(e.get('date') or '?')}\n"
                f"💬 {_html.escape((e.get('snippet') or '')[:250])}")
        try:
            _tg(token, int(chat), text)
            print("alert sent:", e.get("subject"))
        except Exception as ex:
            print("send err:", ex)

    _save_state(seen)
    return 0


if __name__ == "__main__":
    sys.exit(main())
