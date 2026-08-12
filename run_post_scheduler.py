#!/usr/bin/env python3
"""
AIOS Post Scheduler — очередь запланированных постов (data/posts_queue.json).
Раз в минуту (systemd) проверяет: если время настало —
  • TikTok: если приложено видео — публикует через web-upload
  • иначе — шлёт напоминание «время опубликовать…»

Команды в боте:
  «запланируй пост в тикток завтра в 18:00 <описание>»
  «запланируй пост в инстаграм сегодня в 20:00 <описание>»
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

QUEUE = ROOT / "data" / "posts_queue.json"


def _env(key: str) -> str:
    if key in ("AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN"):
        from tg_bot.credentials import secret_from_env_or_credential
        value = secret_from_env_or_credential(
            "AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN", credential="telegram_token"
        )
        if value:
            return value
    if key in ("TELEGRAM_CHAT_ID", "AIOS_OWNER_CHAT_ID", "AIOS_AUTO_CODER_CHAT_ID"):
        from tg_bot.credentials import read_systemd_credential
        value = read_systemd_credential("telegram_owner_chat_id")
        if value:
            return value
    import os
    v = os.environ.get(key, "")
    if v:
        return v
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _load_queue() -> list[dict]:
    try:
        return json.loads(QUEUE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_queue(q: list[dict]) -> None:
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")


def _tg(token: str, chat_id: int, text: str) -> None:
    import html as _html
    payload = {"chat_id": chat_id, "text": _html.escape(text)[:3800],
               "parse_mode": "HTML", "disable_web_page_preview": True}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60):
        pass


def _run_ac(args: list, timeout: int = 240) -> dict:
    py = "/opt/aios/.venv/bin/python"
    cmd = ["xvfb-run", "-a", "-s", "-screen 0 1440x900x24", py, str(ROOT / "run_account_control.py")] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
        out = (r.stdout or "").strip()
        start = out.find("{")
        return json.loads(out[start:]) if start >= 0 else {"status": "error", "error": out[-300:]}
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "timeout"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


def main() -> int:
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    queue = _load_queue()
    if not queue:
        print("Очередь пуста")
        return 0

    now = datetime.now()
    due = [p for p in queue if datetime.fromisoformat(p["at"]) <= now]
    left = [p for p in queue if datetime.fromisoformat(p["at"]) > now]

    for post in due:
        platform = post.get("platform", "tiktok")
        text = post.get("text", "")
        chat_id = post.get("chat_id")
        video = post.get("video", "")
        if not token or not chat_id:
            continue
        try:
            if platform == "tiktok" and video and os.path.exists(video):
                res = _run_ac(["tiktok", "upload", video, "--caption", text, "--confirm"])
                if res.get("status") == "published":
                    _tg(token, int(chat_id), f"🎵 <b>Пост опубликован в TikTok</b>:\n{text[:150]}")
                elif res.get("status") == "draft":
                    _tg(token, int(chat_id), f"⚠️ Видео загружено в TikTok, но кнопка не найдена:\n{text[:100]}")
                else:
                    _tg(token, int(chat_id), f"❌ Не удалось опубликовать TikTok: {res.get('error', '?')}")
            else:
                # напоминание (для IG/FB или нет видео)
                _tg(token, int(chat_id),
                    f"📣 <b>Время опубликовать пост ({platform})</b>:\n{text[:200]}")
            print(f"  [SCHED] {platform}: {text[:50]}")
        except Exception as e:
            print(f"  [SCHED] err: {e}")
            left.append(post)  # повторим позже

    _save_queue(left)
    print(f"Очередь: {len(due)} выполнено, {len(left)} осталось")
    return 0


if __name__ == "__main__":
    sys.exit(main())
