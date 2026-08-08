#!/usr/bin/env python3
"""
AIOS Competitor Monitor — мониторинг конкурентов по товарам склада на OLX.

Для каждой позиции inventory.json находит схожие объявления в olx_http.sqlite
(коллектор) по ключевым словам названия и совместимости, считает рыночные цены
(мин/сред/макс), продавцов и города, сравнивает с нашей ценой.

Вывод:
  - data/competitor_monitor.json — полный отчёт (последний снапшот)
  - CLI: json | report [--telegram] | web

Запуск по cron: 0 9 * * * python run_competitor_monitor.py report --telegram
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
INVENTORY = ROOT / "data" / "inventory.json"
DB = ROOT / "data" / "olx_http.sqlite"
OUT = ROOT / "data" / "competitor_monitor.json"
HTML = ROOT / "data" / "competitor_monitor.html"

# стоп-слова, по которым НЕ матчим (слишком общие)
_STOP = {
    "авторазборк", "разбор", "автозапчастин", "запчастин", "б/у", "бу",
    "продам", "купить", "украин", "київ", "киев", "olx", "новая", "новый",
}


def _load_inventory() -> List[dict]:
    if not INVENTORY.exists():
        return []
    try:
        d = json.loads(INVENTORY.read_text(encoding="utf-8"))
        return d if isinstance(d, list) else []
    except Exception:
        return []


def _tokens(name: str, compatibility: str = "") -> List[str]:
    """Ключевые слова для матчинга: значимые слова названия + совместимости."""
    text = f"{name} {compatibility}".lower()
    # убираем общие слова
    for w in ("в", "сборе", "задний", "передний", "задняя", "передняя", "внутренние",
              "наружные", "с", "и", "на", "за", "от", "в сборе", "б/у"):
        text = text.replace(f" {w} ", " ")
    words = re.findall(r"[а-яёa-z0-9]{3,}", text)
    out = []
    for w in words:
        if w in _STOP or len(w) < 3:
            continue
        out.append(w)
    # первые 4-6 значимых
    return out[:6]


def _match(title: str, tokens: List[str], required: int = 2) -> bool:
    """Совпадение, если title содержит >= required токенов."""
    t = (title or "").lower()
    hits = sum(1 for tok in tokens if tok in t)
    return hits >= required


def _query_for(tokens: List[str]) -> str:
    return " ".join(tokens[:4])


def analyze(only_price_min: bool = False) -> Dict[str, Any]:
    items = _load_inventory()
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT url, title, price_value, city, region, user_name, business, "
        "first_seen, collected_at, photos_json FROM ads WHERE active=1 AND price_value>0"
    ).fetchall()
    con.close()

    results: List[dict] = []
    matched_queries: Dict[str, int] = defaultdict(int)
    for it in items:
        name = it.get("name", "")
        tokens = _tokens(name, it.get("compatibility", ""))
        if not tokens:
            continue
        our_price = float(it.get("price") or 0)
        comps: List[dict] = []
        for (url, title, pv, city, region, uname, business, fs, ca, ph) in rows:
            if not _match(title, tokens):
                continue
            price = float(pv or 0)
            comps.append({
                "title": title[:120],
                "url": url,
                "price": price,
                "city": city or "",
                "region": region or "",
                "seller": uname or "",
                "business": bool(business),
                "first_seen": fs or "",
                "photos": (json.loads(ph) if ph else [])[:3],
            })
        comps.sort(key=lambda x: x["price"])
        q = _query_for(tokens)
        matched_queries[q] += 1
        if not comps:
            results.append({"name": name, "tokens": tokens, "competitors": 0,
                            "our_price": our_price, "market_min": None,
                            "market_median": None, "market_max": None,
                            "position": "no_data", "competitors_list": []})
            continue
        prices = [c["price"] for c in comps]
        median = sorted(prices)[len(prices) // 2]
        position = "no_data"
        if our_price > 0:
            if our_price < prices[0]:
                position = "below_market"
            elif our_price > prices[-1]:
                position = "above_market"
            else:
                position = "in_market"
        results.append({
            "name": name,
            "category": it.get("category", ""),
            "tokens": tokens,
            "competitors": len(comps),
            "our_price": our_price,
            "market_min": prices[0],
            "market_median": median,
            "market_max": prices[-1],
            "position": position,
            "competitors_list": comps[:15],
        })

    # сводка
    total = len(results)
    with_data = [r for r in results if r["competitors"] > 0]
    below = [r for r in with_data if r["position"] == "below_market"]
    above = [r for r in with_data if r["position"] == "above_market"]
    no_comp = [r for r in results if r["competitors"] == 0]
    total_value = sum(float(it.get("price", 0)) * int(it.get("qty", 0)) for it in items)

    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "positions": total,
        "positions_with_competitors": len(with_data),
        "positions_no_competitors": len(no_comp),
        "below_market": len(below),
        "above_market": len(above),
        "in_market": len(with_data) - len(below) - len(above),
        "total_stock_value_uah": total_value,
        "matched_queries": dict(matched_queries),
        "items": results,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _tg(text: str) -> bool:
    import urllib.request
    token = ""
    chat = ""
    for env_path in ("/root/AIOS/.env", "/etc/aios/aios-telegram-bot.env"):
        p = Path(env_path)
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("AIOS_TELEGRAM_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"')
            if line.startswith("AIOS_OWNER_CHAT_ID="):
                chat = line.split("=", 1)[1].strip().strip('"')
    if not token or not chat:
        return False
    try:
        data = json.dumps({"chat_id": int(chat), "text": text[:3800], "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage", data=data,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30):
            return True
    except Exception:
        return False


def report_text(r: Dict[str, Any]) -> str:
    lines = [
        "🆚 <b>Мониторинг конкурентов (OLX)</b>",
        f"📦 Позиций: <b>{r['positions']}</b> · с конкурентами: {r['positions_with_competitors']}",
        f"💰 Наша цена ниже рынка: <b>{r['below_market']}</b> · выше: {r['above_market']} · в рынке: {r['in_market']}",
        "",
        "<b>Переоценены (мы дороже рынка):</b>",
    ]
    above = [i for i in r["items"] if i["position"] == "above_market"][:8]
    for i in above:
        lines.append(f"  ⚠️ {i['name'][:55]} — мы {i['our_price']:.0f} vs рынок до {i['market_max']:.0f} грн")
    if not above:
        lines.append("  — нет")
    lines.append("")
    lines.append("<b>Без конкурентов (можно поднять цену):</b>")
    no_comp = [i for i in r["items"] if i["position"] == "no_data"][:6]
    for i in no_comp:
        lines.append(f"  ✅ {i['name'][:55]} — конкуренты не найдены")
    if not no_comp:
        lines.append("  — нет")
    lines.append("")
    lines.append("<b>Топ дорогих с конкурентами:</b>")
    with_data = [i for i in r["items"] if i["competitors"] > 0]
    for i in sorted(with_data, key=lambda x: -x["our_price"])[:6]:
        lines.append(f"  • {i['name'][:45]} — рынок {i['market_min']:.0f}–{i['market_max']:.0f} (n={i['competitors']}), мы {i['our_price']:.0f}")
    lines.append("")
    lines.append(f"💡 Отчёт: data/competitor_monitor.json · HTML: data/competitor_monitor.html")
    return "\n".join(lines)


def render_html(r: Dict[str, Any]) -> str:
    cards = []
    for i in sorted(r["items"], key=lambda x: -(x["our_price"] or 0)):
        pos = i["position"]
        badge = {
            "below_market": ('<span class="badge ok">Ниже рынка</span>'),
            "above_market": ('<span class="badge out">Выше рынка</span>'),
            "in_market": ('<span class="badge mid">В рынке</span>'),
            "no_data": ('<span class="badge none">Нет данных</span>'),
        }.get(pos, "")
        comp = f"{i['market_min']:.0f}–{i['market_max']:.0f} грн" if i["market_min"] else "—"
        cards.append(f"""
      <div class="card">
        <div class="card-top"><b>{i['name']}</b>{badge}</div>
        <div class="meta">Наша цена: <b>{i['our_price']:.0f} грн</b> · Рынок: {comp} · Конкурентов: {i['competitors']}</div>
        <div class="comps">
          {''.join(f"<div class='comp'><a href='{c['url']}'>{c['title'][:70]}</a> · {c['price']:.0f} грн · {c['seller']} · {c['city']}</div>" for c in i['competitors_list'][:4])}
        </div>
      </div>""")

    return f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Конкуренты — Склад AIOS</title><style>
*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:-apple-system,"Segoe UI",Roboto,sans-serif;background:#f3f4f6;color:#111827;padding:20px}}
header{{background:#111827;color:#fff;padding:16px 20px;border-radius:12px;margin-bottom:16px}}
h1{{font-size:20px}} .sub{{color:#9ca3af;font-size:13px;margin-top:4px}}
.stats{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}}
.stat{{background:#fff;padding:10px 16px;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.stat .n{{font-size:20px;font-weight:700}} .stat .l{{font-size:12px;color:#6b7280}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}}
.card{{background:#fff;border-radius:12px;padding:12px 14px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.card-top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}}
.badge{{font-size:11px;padding:2px 8px;border-radius:999px}}
.badge.ok{{background:#dcfce7;color:#166534}} .badge.out{{background:#fee2e2;color:#991b1b}}
.badge.mid{{background:#fef9c3;color:#854d0e}} .badge.none{{background:#e5e7eb;color:#4b5563}}
.meta{{font-size:12px;color:#6b7280;margin-bottom:8px}}
.comps{{font-size:11px}}
.comp{{padding:3px 0;border-top:1px solid #f3f4f6;color:#4b5563}}
.comp a{{color:#2563eb;text-decoration:none}}
</style></head><body>
<header><h1>🆚 Конкуренты — Склад AIOS</h1>
<div class="sub">Сгенерировано {r['generated_at']} · по данным OLX-коллектора · позиций: {r['positions']}</div></header>
<div class="stats">
  <div class="stat"><div class="n">{r['positions_with_competitors']}</div><div class="l">С конкурентами</div></div>
  <div class="stat"><div class="n">{r['below_market']}</div><div class="l">Ниже рынка</div></div>
  <div class="stat"><div class="n">{r['above_market']}</div><div class="l">Выше рынка</div></div>
  <div class="stat"><div class="n">{r['positions_no_competitors']}</div><div class="l">Нет конкурентов</div></div>
</div>
<div class="grid">{''.join(cards)}</div>
</body></html>"""


def main() -> int:
    args = sys.argv[1:]
    cmd = args[0] if args else "json"
    if cmd == "json":
        r = analyze()
        print(json.dumps({k: v for k, v in r.items() if k != "items"}, ensure_ascii=False, indent=2))
        print(f"items: {len(r['items'])}")
    elif cmd == "report":
        r = analyze()
        HTML.write_text(render_html(r), encoding="utf-8")
        txt = report_text(r)
        print(txt.replace("<b>", "").replace("</b>", ""))
        if "--telegram" in args:
            ok = _tg(txt)
            print(f"TG: {'отправлено' if ok else 'не отправлено'}")
    elif cmd == "web":
        r = analyze()
        HTML.write_text(render_html(r), encoding="utf-8")
        print(f"HTML: {HTML}")
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
