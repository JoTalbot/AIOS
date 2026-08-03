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
        "Напиши объявление для OLX (Украина) про автозапчасть с авторазборки (б/у, рабочая). "
        "Верни ТОЛЬКО JSON без пояснений: "
        "{\"title\": \"заголовок 16-60 символов, конкретный (марка, модель, название детали), НЕ короче 16 символов\", "
        "\"description\": \"описание 3-5 предложений на русском: состояние (б/у, рабочая, без трещин), "
        "для каких авто подходит, что в комплекте, готовность отправить Новой Почтой по Украине, "
        "оплата при получении\", "
        "\"price\": \"реалистичная цена б/у запчасти в гривнах (типичная рыночная, не завышай)\"}. "
        "Цена — ТОЛЬКО в поле price числом, НИКОГДА не упоминай цену в description и title. "
        "Не используй слово «распродажа», «акция», «100%» и прочие кликбейт-приёмы. "
        "Если пользователь указал цену в запросе — используй её. "
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
        # OLX требует заголовок минимум 16 символов
        if len(str(d.get("title") or "").strip()) < 16:
            d["title"] = (str(d.get("title") or "").strip() + " — б/у з авторазборки")[:60]
        # приоритет: цена, указанная пользователем в запросе (число 2-6 цифр, похожее на цену)
        import re as _re
        m_user_price = _re.search(r"\b(\d{2,6})\b\s*(?:грн|грн\.|uah)?\s*$", part, _re.IGNORECASE)
        if m_user_price and int(m_user_price.group(1)) >= 100:
            d["price"] = m_user_price.group(1)
        # fallback: если цена всё ещё пустая — извлечь число из конца
        elif not str(d.get("price") or "").strip():
            m = _re.search(r"(\d{2,6})\s*(грн|грн\.|uah)?\s*$", part, _re.IGNORECASE)
            if m:
                d["price"] = m.group(1)
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


def _load_inventory() -> list[dict]:
    """Позиции склада из data/inventory.json (qty > 0)."""
    p = ROOT / "data" / "inventory.json"
    if not p.exists():
        return []
    try:
        items = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            return []
        return [it for it in items if int(it.get("qty") or 0) > 0]
    except Exception:
        return []


def export_sklad(limit: int = 0, confirm: bool = False, pause: int = 25) -> dict:
    """Массовая выгрузка склада на OLX.

    Берёт позиции из data/inventory.json, генерирует объявления (цена из склада)
    и (если confirm) публикует каждое с паузой между публикациями.
    """
    items = _load_inventory()
    if not items:
        return {"status": "error", "error": "Склад пуст (нет позиций с qty > 0)"}
    if limit > 0:
        items = items[:limit]
    results = []
    ok_cnt = err_cnt = 0
    for i, it in enumerate(items, 1):
        name = (it.get("name") or "").strip()
        price = it.get("price") or ""
        part = f"{name} {price} грн".strip()
        if not name:
            err_cnt += 1
            results.append({"name": "?", "status": "error", "error": "пустое имя"})
            continue
        if confirm:
            photo = (it.get("photo") or "") if isinstance(it.get("photo"), str) else ""
            r = create_ad(part, True, photo or None)
            st = r.get("status")
            if st == "published":
                ok_cnt += 1
            elif st == "draft_created":
                st = "draft"
                err_cnt += 1
            else:
                err_cnt += 1
            results.append({"name": name, "price": price, "status": st,
                            "ad_id": r.get("ad_id", ""), "url": r.get("url", ""),
                            "error": r.get("error", "")})
            # пауза между публикациями (защита от модерации)
            if i < len(items) and pause > 0:
                import time as _t
                print(f"[sklad] пауза {pause}s перед следующей…", flush=True)
                _t.sleep(pause)
        else:
            g = generate(part)
            results.append({"name": name, "price": price,
                            "status": g.get("status", "error"),
                            "title": g.get("title", ""),
                            "price_gen": g.get("price", "")})
            if g.get("status") == "ok":
                ok_cnt += 1
            else:
                err_cnt += 1
    return {"status": "ok", "total": len(results), "ok": ok_cnt, "err": err_cnt,
            "confirm": confirm, "results": results}


def create_ad(part: str, confirm: bool, photo: str | None = None) -> dict:
    """Создать объявление на OLX через Chrome Twin (если телефон подтверждён)."""
    gen = generate(part)
    if gen.get("status") != "ok":
        return gen
    if not confirm:
        return {**gen, "status": "need_confirm", "action": "olx_create"}
    try:
        from aios_core.platforms.olx_chrome_twin_adapter import OLXChromeTwinAdapter
        a = OLXChromeTwinAdapter(config={"olx_login": _env("OLX_LOGIN") or "959052288"})
        _images = [photo] if (photo and Path(photo).exists()) else None

        async def _run_publish():
            try:
                return await a.create_ad(
                    title=gen.get("title", ""),
                    description=gen.get("description", ""),
                    price=str(gen.get("price", "")),
                    images=_images,
                    publish=True,
                )
            finally:
                # закрывать в том же event loop (иначе close() зависает)
                try:
                    await asyncio.wait_for(a.close(), timeout=20)
                except Exception:
                    pass

        r = asyncio.run(_run_publish())
        return r
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
    elif cmd == "export_sklad":
        _args = list(sys.argv[2:])
        confirm = "--confirm" in _args
        limit = 0
        pause = 25
        for _i, _a in enumerate(_args):
            if _a == "--limit" and _i + 1 < len(_args):
                try:
                    limit = int(_args[_i + 1])
                except ValueError:
                    pass
            if _a == "--pause" and _i + 1 < len(_args):
                try:
                    pause = int(_args[_i + 1])
                except ValueError:
                    pass
        print(json.dumps(export_sklad(limit, confirm, pause), ensure_ascii=False))
        return
    elif cmd == "create":
        _args = list(sys.argv[2:])
        photo = ""
        if "--photo" in _args:
            _i = _args.index("--photo")
            if _i + 1 < len(_args):
                photo = _args[_i + 1]
                _args = _args[:_i] + _args[_i + 2:]
        part = " ".join(_args).replace("--confirm", "").strip()
        confirm = "--confirm" in _args
        if not part:
            print(json.dumps({"status": "error", "error": "Укажите деталь"})); return
        print(json.dumps(create_ad(part, confirm, photo), ensure_ascii=False))
    else:
        print(json.dumps({"status": "error", "error": "gen|gen_many|create|export_sklad"}))


if __name__ == "__main__":
    main()
