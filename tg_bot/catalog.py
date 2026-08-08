"""Каталог склада в Telegram — команды «склад», «каталог», «товары».

Показывает статистику склада, список позиций по категориям, неопубликованные
товары и ссылку на HTML-каталог (Stitch / локальный файл).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "inventory.json"
CATALOG_HTML = ROOT / "data" / "inventory_catalog.html"

_TRIGGERS = (
    "склад", "каталог", "товары на складе", "что на складе", "наличие на складе",
    "📦 склад", "витрина", "каталог склада",
)

_DESIGN_TRIGGERS = (
    "дизайн каталога", "дизайн склада", "превью каталога", "превью",
    "покажи каталог", "покажи дизайн", "дизайн",
)

# скриншот, сгенерированный Google Stitch (generate_screen_from_text)
STITCH_DESIGN_PNG = ROOT / "data" / "stitch_catalog_generated.png"
# HTML-версия того же дизайна (для отправки как документ)
STITCH_DESIGN_HTML = ROOT / "data" / "stitch_catalog_generated.html"


def _load() -> list[dict]:
    if not DATA.exists():
        return []
    try:
        data = json.loads(DATA.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _handle_catalog_intent(api, chat_id: int, text: str) -> bool:
    """Обработчик: «склад», «каталог склада», «что на складе» и т.п."""
    t = " ".join(str(text or "").casefold().split())
    if not any(phrase in t for phrase in _TRIGGERS):
        return False
    items = _load()
    if not items:
        api.send_message(chat_id, "📦 Склад пуст.")
        return True

    total_qty = sum(int(it.get("qty", 0)) for it in items)
    total_val = sum(float(it.get("price", 0)) * int(it.get("qty", 0)) for it in items)
    reserved = sum(int(it.get("reserved_qty", 0)) for it in items)
    avail = total_qty - reserved

    # по категориям
    from collections import defaultdict
    by_cat: dict[str, dict] = defaultdict(lambda: {"n": 0, "qty": 0, "val": 0.0})
    for it in items:
        cat = str(it.get("category") or "прочее")
        by_cat[cat]["n"] += 1
        by_cat[cat]["qty"] += int(it.get("qty", 0))
        by_cat[cat]["val"] += float(it.get("price", 0)) * int(it.get("qty", 0))

    lines = [
        "🏬 <b>Склад AIOS</b>",
        f"📦 Позиций: <b>{len(items)}</b> · Единиц: <b>{total_qty}</b> (доступно {avail}, резерв {reserved})",
        f"💰 Общая стоимость: <b>{total_val:,.0f} грн</b>",
        "",
        "<b>По категориям:</b>",
    ]
    for cat, v in sorted(by_cat.items(), key=lambda x: -x[1]["val"]):
        lines.append(f"  • {_esc(cat)}: {v['n']} поз. / {v['qty']} шт / {v['val']:,.0f} грн")

    # неопубликованные: сверяем с data/olx_published.json (там реальные ad_id)
    published_names: set[str] = set()
    pub_path = ROOT / "data" / "olx_published.json"
    if pub_path.exists():
        try:
            for a in json.loads(pub_path.read_text(encoding="utf-8")):
                if isinstance(a, dict) and a.get("name"):
                    published_names.add(str(a["name"]).strip().casefold())
        except Exception:
            pass
    unpub = [it for it in items if str(it.get("name", "")).strip().casefold() not in published_names]
    if unpub:
        lines.append("")
        lines.append(f"⚠️ <b>Не опубликовано на OLX ({len(unpub)}):</b>")
        for it in sorted(unpub, key=lambda x: -float(x.get("price", 0))):
            lines.append(f"  • {_esc(it.get('name',''))} — {it.get('price')} грн")

    if CATALOG_HTML.exists():
        lines.append("")
        lines.append("🌐 HTML-каталог доступен локально (data/inventory_catalog.html) и в Stitch.")

    try:
        api.send_message(chat_id, "\n".join(lines)[:3900])
    except Exception:
        api.send_message(chat_id, "\n".join(lines)[:3900], parse_mode="")
    return True


def _handle_catalog_design_intent(api, chat_id: int, text: str) -> bool:
    """Отправляет превью сгенерированного Stitch-дизайна каталога склада.

    Команды: «дизайн каталога», «превью», «покажи каталог» и т.п.
    """
    t = " ".join(str(text or "").casefold().split())
    if not any(phrase in t for phrase in _DESIGN_TRIGGERS):
        return False

    if STITCH_DESIGN_PNG.exists():
        try:
            api.send_photo(
                chat_id,
                str(STITCH_DESIGN_PNG),
                caption=(
                    "🎨 Дизайн каталога (Google Stitch)\n"
                    "Сгенерирован Stitch AI из DESIGN.md дизайн-системы.\n"
                    "Проект: AIOS Warehouse Catalog"
                ),
            )
        except Exception as e:
            api.send_message(chat_id, f"⚠️ Не удалось отправить скриншот: {e}")
    else:
        api.send_message(chat_id, "⚠️ Превью дизайна ещё не сгенерировано.")

    # HTML-версию отправляем как документ, если есть
    if STITCH_DESIGN_HTML.exists():
        try:
            api.send_document(
                chat_id,
                str(STITCH_DESIGN_HTML),
                caption="📄 HTML дизайна каталога (Stitch) — можно открыть в браузере",
            )
        except Exception:
            pass

    # подсказка (plain text, без HTML)
    api.send_message(
        chat_id,
        "🏬 Склад: команда «склад» — статистика и наличие.\n"
        "📦 OLX: 3 товара не опубликованы (Колесо 2200, Диски Шкода 7000, Кузов 10000).",
    )
    return True
