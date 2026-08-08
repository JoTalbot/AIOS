"""
AIOS Inventory Catalog — каталог склада: нормализация, SKU, обогащение, HTML-витрина.

Слой поверх data/inventory.json (совместим с run_inventory.py: add/reserve/take).
Задачи модуля:
  1. Нормализовать категории (таксономия) и сгенерировать SKU для позиций.
  2. Обогатить поля: brand, condition, weight_kg, compatibility (авто по имени).
  3. Собрать статистику каталога (общая стоимость, по категориям, по статусам).
  4. Сгенерировать самодостаточный HTML-каталог (инлайн-CSS, без внешних ресурсов)
     для загрузки в Google Stitch (upload-to-stitch) или просмотра в браузере.

Категории (таксономия): подвеска, кузов, электрооборудование, система_охлаждения,
двигатель, тормозная_система, оптика, трансмиссия, колеса, салон, прочее.
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "inventory.json"

# ── таксономия категорий ──────────────────────────────────────────────────
CATEGORY_ALIASES: Dict[str, str] = {
    # подвеска
    "подвеск": "подвеска", "рессор": "подвеска", "амортизатор": "подвеска",
    "пружин": "подвеска", "рычаг": "подвеска", "стойк": "подвеска",
    "шрус": "подвеска", "привод": "подвеска", "балк": "подвеска", "тяга": "подвеска",
    # кузов
    "кузов": "кузов", "крыло": "кузов", "капот": "кузов", "двер": "кузов",
    "бампер": "кузов", "порог": "кузов", "рама": "кузов", "панел": "кузов",
    "задняя часть": "кузов", "кузовн": "кузов", "арк": "кузов",
    # электрооборудование
    "генератор": "электрооборудование", "стартер": "электрооборудование",
    "проводк": "электрооборудование", "эбу": "электрооборудование",
    "датчик": "электрооборудование", "катушк": "электрооборудование",
    "свеч": "электрооборудование", "аккумулятор": "электрооборудование",
    "электро": "электрооборудование",
    # система охлаждения
    "радиатор": "система_охлаждения", "охлажд": "система_охлаждения",
    "помп": "система_охлаждения", "термостат": "система_охлаждения",
    "вентилятор": "система_охлаждения",
    # двигатель
    "двигател": "двигатель", "двс": "двигатель", "гбц": "двигатель",
    "блок цилиндров": "двигатель", "коленвал": "двигатель", "поршн": "двигатель",
    # тормозная система
    "тормоз": "тормозная_система", "суппорт": "тормозная_система",
    "колодк": "тормозная_система", "диск тормозн": "тормозная_система",
    "барабан": "тормозная_система",
    # оптика
    "фар": "оптика", "фонар": "оптика", "оптик": "оптика", "стекл": "оптика",
    # трансмиссия
    "кпп": "трансмиссия", "коробк": "трансмиссия", "сцеплен": "трансмиссия",
    "редуктор": "трансмиссия", "мост": "трансмиссия",
    # колеса
    "колес": "колеса", "диск": "колеса", "шина": "колеса", "резин": "колеса",
    "покрышк": "колеса",
    # салон
    "салон": "салон", "сиден": "салон", "кресл": "салон", "рул": "салон",
    "приборн": "салон", "торпед": "салон",
}

CATEGORY_LABELS: Dict[str, str] = {
    "подвеска": "Подвеска", "кузов": "Кузов", "электрооборудование": "Электрооборудование",
    "система_охлаждения": "Система охлаждения", "двигатель": "Двигатель",
    "тормозная_система": "Тормозная система", "оптика": "Оптика",
    "трансмиссия": "Трансмиссия", "колеса": "Колёса и диски",
    "салон": "Салон", "прочее": "Прочее",
}

BRAND_ALIASES: Dict[str, str] = {
    "ваз": "ВАЗ", "lada": "LADA", "лада": "LADA", "газель": "ГАЗель", "газ": "ГАЗ",
    "шкода": "Skoda", "skoda": "Skoda", "bmw": "BMW", "фольксваген": "Volkswagen",
    "vw": "Volkswagen", "mercedes": "Mercedes-Benz", "audi": "Audi", "toyota": "Toyota",
    "fiat": "Fiat", "ford": "Ford", "chevrolet": "Chevrolet", "reno": "Renault",
    "renault": "Renault", "hyundai": "Hyundai", "kia": "Kia", "nissan": "Nissan",
    "fulda": "Fulda", "opel": "Opel",
}

# маркеры для автоопределения бренда по названию
BRAND_KEYWORDS: List[tuple[str, str]] = [
    (r"\bваз\s*\d{3,4}\b", "ВАЗ"), (r"\blada\b", "LADA"), (r"\bгазель\b", "ГАЗель"),
    (r"\bшкода\b", "Skoda"), (r"\bskoda\b", "Skoda"), (r"\bbmw\b", "BMW"),
    (r"\bmercedes\b", "Mercedes-Benz"), (r"\baudi\b", "Audi"), (r"\btoyota\b", "Toyota"),
    (r"\bvolkswagen\b|\bvw\b", "Volkswagen"), (r"\brenault\b|\breno\b", "Renault"),
    (r"\bford\b", "Ford"), (r"\bchevrolet\b", "Chevrolet"), (r"\bnissan\b", "Nissan"),
    (r"\bhyundai\b", "Hyundai"), (r"\bkia\b", "Kia"), (r"\bfulda\b", "Fulda"),
    (r"\bfiat\b", "Fiat"), (r"\bopel\b", "Opel"),
]


def normalize_category(name: str) -> str:
    """Привести категорию позиции к таксономии по ключевым словам в названии."""
    n = unicodedata.normalize("NFKC", (name or "").lower())
    for kw, cat in CATEGORY_ALIASES.items():
        if kw in n:
            return cat
    return "прочее"


def detect_brand(name: str) -> str:
    """Определить бренд по названию (если есть)."""
    n = (name or "").lower()
    for pat, brand in BRAND_KEYWORDS:
        if re.search(pat, n):
            return brand
    return ""


def detect_condition(name: str) -> str:
    """Б/у или новое по названию."""
    n = (name or "").lower()
    if any(w in n for w in ("нов", "новая", "новый")):
        return "new"
    return "used"


def gen_sku(idx: int, name: str) -> str:
    """SKU: AIOS-<номер>-<транслит до 3 слов>."""
    translit = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
    slug = []
    for ch in (name or "").lower():
        if ch.isalnum():
            slug.append(ch)
        elif ch in translit:
            slug.append(translit[ch])
        else:
            slug.append("-")
    words = "".join(slug).split("-")
    words = [w for w in words if w]
    tail = "-".join(words[:3])[:28] or "item"
    return f"AIOS-{idx:03d}-{tail}"


def normalize_items(items: List[dict]) -> List[dict]:
    """Нормализовать список позиций: категории, SKU, бренд, condition, вес-эстимейт.

    Не перезаписывает уже заполненные поля; SKU генерируется только если нет.
    """
    for idx, it in enumerate(items, 1):
        name = it.get("name", "")
        it.setdefault("sku", gen_sku(idx, name))
        if not it.get("category") or it.get("category", "").lower() in ("", "-", "другое", "разное"):
            it["category"] = normalize_category(name)
        else:
            it["category"] = normalize_category(it["category"]) if normalize_category(it["category"]) != "прочее" else normalize_category(name)
        it.setdefault("brand", detect_brand(name))
        it.setdefault("condition", detect_condition(name))
        it.setdefault("description", "")
        it.setdefault("compatibility", "")
        it.setdefault("weight_kg", 0.0)
        it.setdefault("location", "Основной склад")
        it.setdefault("cost_price", round(it.get("price", 0) * 0.6, 2))
        it.setdefault("added", datetime.now().strftime("%Y-%m-%d %H:%M"))
        it.setdefault("stock_status", "in_stock" if it.get("qty", 0) > 0 else "out_of_stock")
    return items


def load() -> List[dict]:
    if DATA.exists():
        try:
            return json.loads(DATA.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save(items: List[dict]) -> None:
    DATA.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def catalog_stats(items: Optional[List[dict]] = None) -> Dict[str, Any]:
    """Статистика каталога: итоги по категориям/статусам/стоимости."""
    items = items if items is not None else load()
    total_qty = sum(int(it.get("qty", 0)) for it in items)
    total_value = round(sum(float(it.get("price", 0)) * int(it.get("qty", 0)) for it in items), 2)
    by_cat: Dict[str, dict] = {}
    for it in items:
        cat = it.get("category", "прочее")
        b = by_cat.setdefault(cat, {"count": 0, "value": 0.0, "qty": 0})
        b["count"] += 1
        b["qty"] += int(it.get("qty", 0))
        b["value"] += float(it.get("price", 0)) * int(it.get("qty", 0))
    for b in by_cat.values():
        b["value"] = round(b["value"], 2)
    published = sum(1 for it in items if it.get("olx_ad_id"))
    return {
        "positions": len(items),
        "total_qty": total_qty,
        "total_value": total_value,
        "published": published,
        "by_category": by_cat,
    }


# ── HTML-витрина каталога ─────────────────────────────────────────────────
def render_catalog_html(items: Optional[List[dict]] = None) -> str:
    """Самодостаточный HTML-каталог склада (инлайн-CSS/JS, без внешних ресурсов).

    Подходит для: предпросмотра в браузере, загрузки в Stitch (upload-to-stitch).
    """
    items = items if items is not None else load()
    stats = catalog_stats(items)
    cats = sorted({it.get("category", "прочее") for it in items})

    def _photo(it: dict) -> str:
        if it.get("photos") and isinstance(it["photos"], list):
            for p in it["photos"]:
                if Path(str(p)).exists():
                    return str(p)
        p = it.get("photo")
        if p and Path(str(p)).exists():
            return str(p)
        return ""

    def _img_tag(it: dict) -> str:
        ph = _photo(it)
        if ph:
            # данные в base64, чтобы HTML был самодостаточным
            try:
                import base64
                b64 = base64.b64encode(Path(ph).read_bytes()).decode()
                ext = Path(ph).suffix.lower().lstrip(".") or "jpg"
                if ext == "jpeg":
                    ext = "jpg"
                mime = "image/png" if ext == "png" else "image/jpeg"
                return f'<img src="data:{mime};base64,{b64}" alt="" loading="lazy">'
            except Exception:
                return '<div class="ph ph-empty">📷</div>'
        return '<div class="ph ph-empty">📷</div>'

    cards = []
    for it in sorted(items, key=lambda x: -float(x.get("price", 0))):
        cat = it.get("category", "прочее")
        cat_label = CATEGORY_LABELS.get(cat, cat)
        price = float(it.get("price", 0))
        qty = int(it.get("qty", 0))
        avail = qty - int(it.get("reserved_qty", 0))
        badge = '<span class="badge out">Нет в наличии</span>' if avail <= 0 else f'<span class="badge ok">В наличии: {avail}</span>'
        brand = it.get("brand") or "—"
        cond = "Б/у" if it.get("condition") != "new" else "Новое"
        cards.append(f"""
      <div class="card" data-cat="{cat}">
        {_img_tag(it)}
        <div class="card-body">
          <div class="card-top"><span class="sku">{it.get('sku','')}</span>{badge}</div>
          <h3>{it.get('name','')}</h3>
          <div class="meta"><span>Бренд: {brand}</span><span>{cond}</span></div>
          <div class="price">{price:,.0f} грн</div>
          <div class="cat">{cat_label}</div>
        </div>
      </div>""")

    cat_buttons = "".join(
        f'<button class="chip" data-filter="{c}" onclick="flt(this)">{CATEGORY_LABELS.get(c, c)}</button>'
        for c in cats
    )
    cat_rows = "".join(
        f"<tr><td>{CATEGORY_LABELS.get(c, c)}</td><td>{stats['by_category'].get(c, {}).get('count', 0)}</td>"
        f"<td>{stats['by_category'].get(c, {}).get('qty', 0)}</td>"
        f"<td>{stats['by_category'].get(c, {}).get('value', 0):,.0f} грн</td></tr>"
        for c in cats
    )

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Склад AIOS — Каталог</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, "Segoe UI", Roboto, sans-serif; background: #f3f4f6; color: #111827; }}
  header {{ background: #111827; color: #fff; padding: 20px 28px; }}
  header h1 {{ font-size: 22px; }}
  header .sub {{ color: #9ca3af; font-size: 13px; margin-top: 4px; }}
  .stats {{ display: flex; gap: 16px; padding: 16px 28px; flex-wrap: wrap; }}
  .stat {{ background: #fff; border-radius: 12px; padding: 12px 18px; box-shadow: 0 1px 3px rgba(0,0,0,.08); min-width: 130px; }}
  .stat .n {{ font-size: 22px; font-weight: 700; }}
  .stat .l {{ font-size: 12px; color: #6b7280; }}
  .toolbar {{ padding: 8px 28px; display: flex; gap: 8px; flex-wrap: wrap; }}
  .chip {{ border: 1px solid #d1d5db; background: #fff; padding: 6px 14px; border-radius: 999px; cursor: pointer; font-size: 13px; }}
  .chip.active {{ background: #2563eb; color: #fff; border-color: #2563eb; }}
  #search {{ margin-left: auto; padding: 6px 12px; border: 1px solid #d1d5db; border-radius: 8px; width: 220px; font-size: 13px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; padding: 20px 28px 40px; }}
  .card {{ background: #fff; border-radius: 14px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .card .ph {{ height: 150px; background: #e5e7eb; display: flex; align-items: center; justify-content: center; font-size: 34px; color: #9ca3af; }}
  .card img {{ width: 100%; height: 150px; object-fit: cover; }}
  .card-body {{ padding: 12px 14px; }}
  .card-top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
  .sku {{ font-size: 11px; color: #6b7280; font-family: monospace; }}
  .badge {{ font-size: 11px; padding: 2px 8px; border-radius: 999px; }}
  .badge.ok {{ background: #dcfce7; color: #166534; }}
  .badge.out {{ background: #fee2e2; color: #991b1b; }}
  .card h3 {{ font-size: 14px; line-height: 1.35; margin-bottom: 6px; }}
  .meta {{ display: flex; gap: 10px; font-size: 12px; color: #6b7280; margin-bottom: 8px; }}
  .price {{ font-size: 18px; font-weight: 700; color: #111827; }}
  .cat {{ font-size: 11px; color: #2563eb; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  th, td {{ padding: 10px 14px; text-align: left; font-size: 13px; border-bottom: 1px solid #f3f4f6; }}
  th {{ background: #f9fafb; color: #6b7280; font-size: 12px; text-transform: uppercase; }}
  section {{ padding: 0 28px 24px; }}
  section h2 {{ font-size: 16px; margin-bottom: 12px; }}
  .hidden {{ display: none !important; }}
</style>
</head>
<body>
<header>
  <h1>🏬 Склад AIOS — Каталог</h1>
  <div class="sub">Сгенерировано {datetime.now().strftime('%Y-%m-%d %H:%M')} · данные: data/inventory.json · Google Stitch</div>
</header>
<div class="stats">
  <div class="stat"><div class="n">{stats['positions']}</div><div class="l">Позиций</div></div>
  <div class="stat"><div class="n">{stats['total_qty']}</div><div class="l">Единиц на складе</div></div>
  <div class="stat"><div class="n">{stats['total_value']:,.0f} грн</div><div class="l">Общая стоимость</div></div>
  <div class="stat"><div class="n">{stats['published']}</div><div class="l">Опубликовано на OLX</div></div>
</div>
<div class="toolbar">
  <button class="chip active" data-filter="all" onclick="flt(this)">Все</button>
  {cat_buttons}
  <input id="search" placeholder="Поиск по названию / SKU…" oninput="srch(this.value)">
</div>
<div class="grid" id="grid">
  {''.join(cards)}
</div>
<section>
  <h2>Сводка по категориям</h2>
  <table>
    <thead><tr><th>Категория</th><th>Позиций</th><th>Единиц</th><th>Стоимость</th></tr></thead>
    <tbody>{cat_rows}</tbody>
  </table>
</section>
<script>
  var cur = "all";
  function flt(el) {{
    cur = el.dataset.filter;
    document.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
    el.classList.add("active");
    apply();
  }}
  function srch(q) {{
    document.querySelectorAll(".card").forEach(c => {{
      c.dataset._q = (c.textContent || "").toLowerCase();
      c.dataset._m = c.dataset._q.indexOf((q||"").toLowerCase()) >= 0;
    }});
    apply();
  }}
  function apply() {{
    document.querySelectorAll(".card").forEach(c => {{
      var okCat = cur === "all" || c.dataset.cat === cur;
      var okQ = c.dataset._m === undefined || c.dataset._m === true || c.dataset._m === "true";
      c.classList.toggle("hidden", !(okCat && okQ));
    }});
  }}
</script>
</body>
</html>"""


def main() -> None:
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "normalize":
        items = load()
        items = normalize_items(items)
        save(items)
        print(f"Нормализовано позиций: {len(items)}")
        print(json.dumps(catalog_stats(items), ensure_ascii=False, indent=2))
    elif cmd == "stats":
        print(json.dumps(catalog_stats(), ensure_ascii=False, indent=2))
    elif cmd == "html":
        out = ROOT / "data" / "inventory_catalog.html"
        out.write_text(render_catalog_html(), encoding="utf-8")
        print(f"HTML каталог: {out} ({out.stat().st_size} байт)")
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
