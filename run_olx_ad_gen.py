#!/usr/bin/env python3
"""
AIOS OLX Ad Generator — генерирует текст объявления OLX через LLM
и (при подтверждённом телефоне) создаёт объявление на olx.ua.

  python run_olx_ad_gen.py gen <деталь>            — сгенерировать {title, desc, price}
  python run_olx_ad_gen.py create <деталь> [--confirm] — создать объявление
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


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


def _llm(prompt: str) -> str:
    """Одиночный LLM-вызов через балансер/OpenRouter."""
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
                        system="Ты пишешь объявления для OLX. Отвечай на русском.",
                        max_tokens=500, temperature=0.4, task_type="chat")
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
                "max_tokens": 500, "temperature": 0.4,
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


def generate(part: str) -> dict:
    """Сгенерировать объявление из короткого названия детали."""
    prompt = (
        "Напиши объявление для OLX (Украина) про автозапчасть. Верни ТОЛЬКО JSON без пояснений: "
        "{\"title\": \"заголовок до 60 символов\", \"description\": \"описание 2-4 предложения, "
        "на русском, с указанием состояния, совместимости и готовности к отправке Новой Почтой\", "
        "\"price\": \"число в гривнах\"}. Цена в грн, НЕ пиши слова «рублей» или «грн» в price. "
        f"Деталь: {part}"
    )
    resp = _llm(prompt)
    try:
        start = resp.find("{")
        end = resp.rfind("}") + 1
        d = json.loads(resp[start:end]) if start >= 0 and end > start else {}
        d.setdefault("title", part[:60])
        d.setdefault("description", "")
        d.setdefault("price", "")
        return {"status": "ok", **d, "part": part}
    except Exception:
        return {"status": "error", "error": "Не удалось сгенерировать (LLM)", "part": part}


def generate_many(parts: list[str]) -> dict:
    """Массовая генерация из списка деталей."""
    out = []
    for p in parts:
        p = p.strip().strip(".,")
        if not p:
            continue
        r = generate(p)
        out.append(r)
    return {"status": "ok", "ads": out, "count": len(out)}


def create_ad(part: str, confirm: bool) -> dict:
    """Создать объявление на OLX через Chrome Twin (если телефон подтверждён)."""
    gen = generate(part)
    if gen.get("status") != "ok":
        return gen
    if not confirm:
        return {"status": "need_confirm", "action": "olx_create", **gen}
        try:
            from aios_core.platforms.olx_chrome_twin_adapter import OLXChromeTwinAdapter
            a = OLXChromeTwinAdapter(config={"olx_login": _env("OLX_LOGIN") or "959052288"})
            try:
                r = asyncio.run(a.create_ad(
                    title=gen.get("title", ""),
                    description=gen.get("description", ""),
                    price=str(gen.get("price", "")),
                    publish=confirm,
                ))
                return r
            finally:
                asyncio.run(a.close())
        except Exception as e:
            return {"status": "error", "error": str(e)[:300]}


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "gen"
    if cmd == "gen":
        part = " ".join(sys.argv[2:])
        if not part:
            print(json.dumps({"status": "error", "error": "Укажите деталь"})); return
        print(json.dumps(generate(part), ensure_ascii=False))
    elif cmd == "gen_many":
        # список из аргументов, разделённых «;» или строк
        parts = " ".join(sys.argv[2:]).split(";")
        print(json.dumps(generate_many(parts), ensure_ascii=False))
    elif cmd == "create":
        part = " ".join(sys.argv[2:]).replace("--confirm", "").strip()
        confirm = "--confirm" in sys.argv
        if not part:
            print(json.dumps({"status": "error", "error": "Укажите деталь"})); return
        print(json.dumps(create_ad(part, confirm), ensure_ascii=False))
    else:
        print(json.dumps({"status": "error", "error": "gen|gen_many|create"}))


if __name__ == "__main__":
    main()
