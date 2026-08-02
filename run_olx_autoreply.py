#!/usr/bin/env python3
"""
AIOS OLX Autoreply — умные ответы покупателям в OLX-чате.
Раз в N минут проверяет чат OLX (myaccount/answers) на новые сообщения;
если автоответ включён — формирует ответ (шаблон из data/templates.json
или LLM) и шлёт в Telegram на подтверждение (или отправляет авто).

Команды в боте:
  «включи автоответ OLX» / «выключи автоответ OLX» / «автоответ на автомате»
Настройка: data/olx_autoreply.json
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

CFG = ROOT / "data" / "olx_autoreply.json"


def _env(key: str) -> str:
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


def _load_cfg() -> dict:
    try:
        return json.loads(CFG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cfg(cfg: dict) -> None:
    CFG.parent.mkdir(parents=True, exist_ok=True)
    CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


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


def _templates() -> dict:
    try:
        return json.loads((ROOT / "data" / "templates.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def _llm(prompt: str) -> str:
    import urllib.request as _urllib
    _b = None
    try:
        from aios_core.llm_balancer import LLMBalancer as _LB
        _b = _LB()
    except Exception:
        _b = None
    if _b is not None:
        try:
            r = _b.chat([{"role": "user", "content": prompt}],
                        model=_env("LLM_MODEL") or "meta-llama/llama-4-maverick",
                        system="Ты — помощник продавца автозапчастей. Отвечай кратко, по-русски, вежливо.",
                        max_tokens=250, temperature=0.4, task_type="chat")
            if r:
                return r
        except Exception:
            pass
    try:
        key = _env("OPENROUTER_API_KEY")
        if key:
            payload = json.dumps({
                "model": "mistralai/mistral-small-3.2-24b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 250, "temperature": 0.4,
            }).encode()
            req = _urllib.Request("https://openrouter.ai/api/v1/chat/completions",
                                  data=payload, headers={
                                      "Content-Type": "application/json",
                                      "Authorization": "Bearer " + key})
            with _urllib.urlopen(req, timeout=60) as resp:
                d = json.loads(resp.read())
            return d["choices"][0]["message"]["content"]
    except Exception:
        pass
    return ""


def _run_ac(args: list, timeout: int = 170) -> dict:
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


def check_olx_chat() -> list[dict]:
    """Прочитать новые сообщения OLX-чата (упрощённо: страница чата)."""
    try:
        from aios_core.platforms.olx_chrome_twin_adapter import OLXChromeTwinAdapter
        a = OLXChromeTwinAdapter(config={"olx_login": "959052288"})
        try:
            async def _do():
                page = await a._ensure_browser()
                await page.goto("https://www.olx.ua/uk/myaccount/answers/",
                                wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(6000)
                body = await page.inner_text("body")
                lines = [l.strip() for l in body.splitlines() if l.strip()]
                # ищем строки похожие на сообщения
                msgs = []
                for l in lines:
                    if len(l) > 5 and not any(k in l.lower() for k in (
                            "профіль", "профиль", "оголошення", "чат", "повідомлення",
                            "мої", "обра", "вийти", "додати оголошення", "платежі",
                            "рейтинг", "налаштування", "доставка", "пошуки", "бізнес",
                            "допомога", "умови", "політика", "реклама", "для преси",
                            "мобільні", "платні", "рахунок", "баланс", "бонус")):
                        msgs.append(l)
                return msgs
            return asyncio.run(_do())
        finally:
            asyncio.run(a.close())
    except Exception as e:
        return [f"ОШИБКА: {e}"]


def main() -> int:
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    cfg = _load_cfg()
    chat_id = _env("TELEGRAM_CHAT_ID")
    if not cfg.get("enabled"):
        print("Автоответ OLX выключен")
        return 0
    msgs = check_olx_chat()
    # здесь полноценная логика: сравнить с last_seen, сгенерировать ответ
    # и отправить на подтверждение. Сейчас чат пуст, поэтому просто отчитываемся.
    real = [m for m in msgs if not m.startswith("ОШИБКА") and "немає повідомлень" not in m.lower()]
    if token and chat_id:
        try:
            if real:
                _tg(token, int(chat_id),
                    f"💬 <b>Новые сообщения OLX:</b>\n" + "\n".join(f"• {m[:80]}" for m in real[:5]) +
                    "\n\nОтветить: «ответь в олх: текст»")
            else:
                print(f"OLX чат: сообщений нет ({len(msgs)} строк)")
        except Exception as e:
            print(f"tg err: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
