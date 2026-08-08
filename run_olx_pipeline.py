#!/usr/bin/env python3
"""
AIOS OLX Pipeline v21.0 — полный цикл: склад → объявление → продажа → ТТН.

Связывает существующие звенья:
  run_inventory.py      — остатки, резервы, списания
  run_olx_ad_gen.py     — LLM-генерация и публикация объявлений (Chrome Twin)
  sales_lifecycle       — статусы сделок, авто-деактивация объявлений

Безопасность: публикация объявлений ТОЛЬКО с --confirm (реальный пост в OLX).
Все складские операции локальны и идемпотентны.

Usage:
  python run_olx_pipeline.py scan                    # какие позиции не опубликованы
  python run_olx_pipeline.py publish --confirm       # опубликовать неопубликованное
  python run_olx_pipeline.py sold "Радиатор ВАЗ 2109" --qty 1 --sale-id sale-x --ttn 2045...
  python run_olx_pipeline.py cycle                   # sync продаж: shipped→списание, delivered→финал
  python run_olx_pipeline.py report [--telegram]     # воронка склада/объявлений/сделок
  python run_olx_pipeline.py daemon --interval 900   # cycle в цикле (без publish)
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import run_inventory as inv  # noqa: E402
import run_olx_ad_gen as adgen  # noqa: E402

DATA = ROOT / "data"
PUBLISHED = DATA / "olx_published.json"
STATE = DATA / "olx_pipeline_state.json"


# ─────────────────────────────────────────────────────────────────────────────
def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _env(name: str) -> str:
    import os
    v = os.environ.get(name)
    if v:
        return v
    ef = ROOT / ".env"
    if ef.exists():
        for line in ef.read_text(encoding="utf-8").splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _tg(text: str) -> bool:
    import urllib.request
    token, chat = _env("TELEGRAM_BOT_TOKEN"), _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=json.dumps({"chat_id": int(chat), "text": text,
                             "parse_mode": "HTML", "disable_web_page_preview": True}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10):
            return True
    except Exception:
        return False


def _published_names() -> set[str]:
    pubs = _load(PUBLISHED, [])
    return {str(p.get("name") or "").casefold() for p in pubs if isinstance(p, dict)}


def unpublished_in_stock() -> list[dict]:
    """Складские позиции с доступным остатком, которых нет среди опубликованных."""
    items = inv._load()
    pubs = _published_names()
    out = []
    for it in items:
        if inv.available_qty(it) > 0 and str(it.get("name") or "").casefold() not in pubs:
            out.append(it)
    return out


# ─────────────────────────────────────────────────────────────────────────────
def cmd_scan() -> dict:
    rows = unpublished_in_stock()
    res = {
        "status": "ok",
        "unpublished_count": len(rows),
        "items": [{"name": it["name"], "available": inv.available_qty(it), "price": it.get("price")} for it in rows],
    }
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return res


def cmd_publish(confirm: bool) -> dict:
    """Опубликовать неопубликованные складские позиции. confirm=True → реальный пост."""
    rows = unpublished_in_stock()
    pubs = _load(PUBLISHED, [])
    results = []
    for it in rows:
        name = it["name"]
        if not confirm:
            results.append({"name": name, "status": "would_publish"})
            continue
        # мультифото: передаём все photos позиции, если есть (create_ad умеет галерею)
        _photos = it.get("photos") or ([it["photo"]] if it.get("photo") else None)
        r = adgen.create_ad(name, confirm=True, photo=_photos or None)
        ok = r.get("status") in ("ok", "published", "created") or r.get("ad_id")
        results.append({"name": name, "status": r.get("status"), "ad_id": r.get("ad_id"), "url": r.get("url")})
        if ok:
            pubs.append({
                "name": name, "ad_id": r.get("ad_id"), "url": r.get("url"),
                "title": r.get("title"), "price": it.get("price"),
                "published_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            })
            _save(PUBLISHED, pubs)
            _tg(f"🛒 <b>OLX опубликовано</b>: {name}\n{r.get('url') or ''}")
        time.sleep(3)  # respect OLX
    res = {"status": "ok", "processed": len(rows), "results": results, "confirmed": confirm}
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return res


def cmd_sold(name: str, qty: int, sale_id: str, ttn: str) -> dict:
    """Продажа: резерв на складе под сделку/ТТН."""
    parts = [p for p in (name,) ]
    target = inv._find(inv._load(), name)
    if not target:
        # мягкий поиск по подстроке
        for it in inv._load():
            if name.casefold() in str(it.get("name", "")).casefold():
                target = it
                name = it["name"]
                break
    if not target:
        res = {"status": "error", "error": f"Позиция «{name}» на складе не найдена"}
        print(json.dumps(res, ensure_ascii=False))
        return res
    r = inv.reserve(name, qty=qty, sale_id=sale_id, ttn=ttn)
    if r.get("status") == "ok":
        _tg(f"📦 <b>Резерв склада</b>: {qty} шт «{name}» → сделка {sale_id or '—'} ТТН {ttn or '—'}")
    print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
    return r


def cmd_cycle(notify: bool = True) -> dict:
    """Синхронизация: shipped→списание склада, delivered→финал, qty=0→деактивация."""
    sales = _load(DATA / "sales_lifecycle.json", [])
    actions = []
    for s in sales:
        st = str(s.get("status") or "")
        sid = s.get("id") or ""
        item_name = s.get("item") or ""
        if st in ("shipped", "in_transit"):
            r = inv.commit_reservation(sid, item_name)
            if r.get("status") == "ok" and not r.get("idempotent"):
                actions.append({"sale": sid, "item": item_name, "action": "stock_committed", "msg": r.get("msg")})
        elif st in ("delivered", "return_received"):
            # финал: снять остаточный резерв, если висел
            r = inv.commit_reservation(sid, item_name)
            if r.get("status") == "ok" and not r.get("idempotent"):
                actions.append({"sale": sid, "item": item_name, "action": "final_commit"})
    # свернуть: товары с available=0, но опубликованные — пометить к деактивации
    low = [it["name"] for it in inv._load() if inv.available_qty(it) == 0]
    state = _load(STATE, {"runs": 0, "actions": []})
    state["runs"] = int(state.get("runs", 0)) + 1
    state["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
    state.setdefault("actions", []).extend(actions)
    state["actions"] = state["actions"][-200:]
    _save(STATE, state)
    res = {"status": "ok", "stock_actions": actions, "out_of_stock": low, "run": state["runs"]}
    if notify and actions:
        txt = "🔄 <b>OLX Pipeline cycle</b>\n" + "\n".join(f"• {a['item']}: {a['action']}" for a in actions)
        if low:
            txt += f"\n⚠️ Нет в наличии: {', '.join(low[:5])}"
        _tg(txt)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return res


def cmd_report(telegram: bool = False) -> dict:
    items = inv._load()
    pubs = _load(PUBLISHED, [])
    sales = _load(DATA / "sales_lifecycle.json", [])
    by_status: dict[str, int] = {}
    for s in sales:
        st = str(s.get("status") or "?")
        by_status[st] = by_status.get(st, 0) + 1
    pub_names = _published_names()
    res = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "inventory": {
            "positions": len(items),
            "total_qty": sum(int(i.get("qty") or 0) for i in items),
            "available_qty": sum(inv.available_qty(i) for i in items),
            "reserved_qty": sum(inv.reserved_qty(i) for i in items),
            "value_uah": round(sum(float(i.get("price") or 0) * inv.available_qty(i) for i in items), 2),
        },
        "ads_published": len(pubs),
        "unpublished_in_stock": len([i for i in items if inv.available_qty(i) > 0 and str(i.get("name", "")).casefold() not in pub_names]),
        "sales_by_status": by_status,
        "pipeline_runs": _load(STATE, {}).get("runs", 0),
    }
    if telegram:
        invr = res["inventory"]
        txt = (f"🛒 <b>OLX Pipeline</b>\n"
               f"Склад: {invr['positions']} поз. / {invr['available_qty']} шт на {invr['value_uah']:.0f} грн "
               f"(резерв {invr['reserved_qty']})\n"
               f"Объявлений: {res['ads_published']}, ждут публикации: {res['unpublished_in_stock']}\n"
               f"Сделки: " + ", ".join(f"{k}×{v}" for k, v in by_status.items()) + "\n#склад #olx")
        res["telegram_sent"] = _tg(txt)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return res


def main() -> int:
    args = sys.argv[1:]
    cmd = args[0] if args else "report"
    if cmd == "scan":
        cmd_scan()
    elif cmd == "publish":
        cmd_publish("--confirm" in args)
    elif cmd == "sold" and len(args) >= 2:
        name = args[1]
        qty = int(args[args.index("--qty") + 1]) if "--qty" in args else 1
        sale_id = args[args.index("--sale-id") + 1] if "--sale-id" in args else f"sale-{int(time.time())}"
        ttn = args[args.index("--ttn") + 1] if "--ttn" in args else ""
        cmd_sold(name, qty, sale_id, ttn)
    elif cmd == "cycle":
        cmd_cycle()
    elif cmd == "report":
        cmd_report("--telegram" in args)
    elif cmd == "daemon":
        interval = int(args[args.index("--interval") + 1]) if "--interval" in args else 900
        print(f"🚀 OLX Pipeline daemon interval {interval}s (cycle only, publish вручную)", flush=True)
        while True:
            try:
                cmd_cycle(notify=True)
            except Exception as e:
                print(f"cycle error: {e}", file=sys.stderr, flush=True)
            time.sleep(interval)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
