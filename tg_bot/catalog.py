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
    "📦 склад", "витрина", "каталог склада", "товары", "позиции на складе",
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
        api.send_message(chat_id, "\n".join(lines)[:3900], reply_markup=_catalog_inline_keyboard())
    except Exception:
        try:
            api.send_message(chat_id, "\n".join(lines)[:3900], parse_mode="", reply_markup=_catalog_inline_keyboard())
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


def _catalog_inline_keyboard() -> dict:
    """Inline-кнопки быстрой навигации по каталогу."""
    return {
        "inline_keyboard": [
            [
                {"text": "🏬 Склад", "callback_data": "cat_warehouse"},
                {"text": "🆚 Конкуренты", "callback_data": "cat_competitors"},
            ],
            [
                {"text": "🎨 Дизайн", "callback_data": "cat_design"},
                {"text": "💼 Фриланс", "callback_data": "cat_freelance"},
            ],
        ]
    }


def _handle_competitors_intent(api, chat_id: int, text: str) -> bool:
    """«конкуренты», «цены конкурентов», «мониторинг цен» — отчёт по конкурентам."""
    t = " ".join(str(text or "").casefold().split())
    if not any(ph in t for ph in ("конкурент", "цены конкурент", "мониторинг цен", "рынок", "🆚")):
        return False
    mon_path = ROOT / "data" / "competitor_monitor.json"
    if not mon_path.exists():
        api.send_message(chat_id, "⚠️ Нет данных мониторинга. Запусти: python run_competitor_monitor.py")
        return True
    try:
        mon = json.loads(mon_path.read_text(encoding="utf-8"))
    except Exception:
        api.send_message(chat_id, "⚠️ Ошибка чтения мониторинга.")
        return True

    items = mon.get("items", [])
    below = [i for i in items if i["position"] == "below_market"]
    above = [i for i in items if i["position"] == "above_market"]
    no_comp = [i for i in items if i.get("competitors", 0) == 0]

    lines = [
        "🆚 <b>Конкуренты (OLX)</b>",
        f"🔎 Позиций с конкурентами: <b>{mon.get('positions_with_competitors', 0)}</b> из {mon.get('positions', 0)}",
        f"⬇️ Наша цена ниже рынка: <b>{len(below)}</b> · ⬆️ выше: <b>{len(above)}</b> · без конкуренции: <b>{len(no_comp)}</b>",
        "",
    ]
    if below:
        lines.append("<b>Можно поднять цену:</b>")
        for i in sorted(below, key=lambda x: -x.get("our_price", 0))[:5]:
            lines.append(
                f"  • {_esc(i['name'][:45])} — мы {i['our_price']:.0f}, рынок {i.get('market_min', 0):.0f}–{i.get('market_max', 0):.0f}"
            )
    if above:
        lines.append("")
        lines.append("<b>Мы дороже рынка:</b>")
        for i in sorted(above, key=lambda x: -x.get("our_price", 0))[:3]:
            lines.append(f"  ⚠️ {_esc(i['name'][:45])} — мы {i['our_price']:.0f}, рынок до {i.get('market_max', 0):.0f}")
    lines.append("")
    lines.append(f"📅 Обновлено: {mon.get('generated_at', '—')}")
    lines.append("💡 Сводка по позициям — в HTML-отчёте data/competitor_monitor.html")

    try:
        api.send_message(chat_id, "\n".join(lines), reply_markup=_catalog_inline_keyboard())
    except Exception:
        api.send_message(chat_id, "\n".join(lines).replace("<b>", "").replace("</b>", ""))
    return True


# ── Пагинация товаров и карточка товара (v22.8) ────────────────────────────
_PAGE_SIZE = 10

_ITEMS_TRIGGERS = (
    "товары", "позиции на складе", "список товаров", "все товары", "что есть",
)

_ITEM_CARD_TRIGGERS = ("товар ", "деталь ", "карточка ")


def _send_items_page(api, chat_id: int, offset: int = 0) -> None:
    """Список товаров склада с пагинацией (inline-кнопки ⬅️/➡️)."""
    items = _load()
    if not items:
        api.send_message(chat_id, "📦 Склад пуст.")
        return
    items = sorted(items, key=lambda x: -float(x.get("price", 0)))
    total = len(items)
    offset = max(0, min(offset, total - 1))
    page = items[offset:offset + _PAGE_SIZE]
    total_pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
    cur_page = offset // _PAGE_SIZE + 1

    lines = [
        f"🏬 <b>Товары склада</b> ({total} поз.) — стр. {cur_page}/{total_pages}",
        "",
    ]
    for i, it in enumerate(page, offset + 1):
        avail = int(it.get("qty", 0)) - int(it.get("reserved_qty", 0))
        lines.append(f"{i}. <b>{_esc(it.get('name', ''))}</b> — {it.get('price')} грн · {avail} шт")
    lines.append("")
    lines.append("ℹ️ «товар <название>» — карточка с фото и описанием")

    row = []
    if offset > 0:
        row.append({"text": "⬅️", "callback_data": f"cat_items_{max(0, offset - _PAGE_SIZE)}"})
    row.append({"text": f"{cur_page}/{total_pages}", "callback_data": "noop"})
    if offset + _PAGE_SIZE < total:
        row.append({"text": "➡️", "callback_data": f"cat_items_{offset + _PAGE_SIZE}"})
    kb = {
        "inline_keyboard": [
            row,
            [{"text": "🏬 Склад", "callback_data": "cat_warehouse"},
             {"text": "🆚 Конкуренты", "callback_data": "cat_competitors"}],
        ]
    }
    try:
        api.send_message(chat_id, "\n".join(lines), reply_markup=kb)
    except Exception:
        api.send_message(chat_id, "\n".join(lines).replace("<b>", "").replace("</b>", ""))


def _send_item_card(api, chat_id: int, query: str) -> None:
    """Карточка товара: фото + цена + совместимость + описание."""
    items = _load()
    q = query.strip().casefold()
    found = None
    for it in items:
        if it.get("name", "").strip().casefold() == q:
            found = it
            break
    if not found:
        for it in items:
            name = it.get("name", "").strip().casefold()
            compat = str(it.get("compatibility", "")).casefold()
            if q in name or q in compat:
                found = it
                break
    if not found:
        api.send_message(chat_id, f"🔍 Товар «{query}» не найден. Напишите «товары» для списка.")
        return

    ph = found.get("photos") or ([found["photo"]] if found.get("photo") else [])
    photo_path = next((str(p) for p in ph if Path(p).exists()), None)

    lines = [
        f"🏷 <b>{_esc(found.get('name', ''))}</b>",
        f"💰 Цена: <b>{found.get('price')} грн</b>"
        + (f" · опт от {found.get('price_min')}" if found.get("price_min") else ""),
        f"📦 В наличии: {int(found.get('qty', 0)) - int(found.get('reserved_qty', 0))} шт",
        f"🏷 {_esc(found.get('category', ''))}"
        + (f" · {_esc(found.get('brand', ''))}" if found.get("brand") else ""),
    ]
    if found.get("compatibility"):
        lines.append(f"🚗 Совместимость: {_esc(found['compatibility'])}")
    if found.get("location"):
        lines.append(f"📍 Место: {_esc(found['location'])}")
    if found.get("description"):
        lines.append(f"📝 {_esc(found['description'])}")
    lines.append(f"🔖 SKU: {_esc(found.get('sku', ''))}")
    caption = "\n".join(lines)[:950]

    if photo_path:
        try:
            api.send_photo(chat_id, photo_path, caption=caption)
            return
        except Exception:
            pass
    api.send_message(chat_id, caption)


def _handle_items_intent(api, chat_id: int, text: str) -> bool:
    """«товары», «список товаров», «позиции на складе» — пагинированный список."""
    t = " ".join(str(text or "").casefold().split())
    if not any(ph in t for ph in _ITEMS_TRIGGERS):
        return False
    try:
        _send_items_page(api, chat_id, 0)
    except Exception as e:
        api.send_message(chat_id, f"⚠️ Ошибка списка товаров: {e}")
    return True


def _handle_item_card_intent(api, chat_id: int, text: str) -> bool:
    """«товар <название>», «деталь <название>» — карточка с фото.

    Не перехватывает команды добавления/списания: «добавь деталь …»,
    «спиши деталь …» и т.п. — они обрабатываются складскими интентами.
    """
    t = " ".join(str(text or "").casefold().split())
    # пропускаем действия со складом
    for act in ("добавь", "создай", "спиши", "продай", "зарезервируй", "измен"):
        if t.startswith(act):
            return False
    for trig in _ITEM_CARD_TRIGGERS:
        if trig in t:
            query = t.split(trig, 1)[-1].strip()
            if len(query) >= 2:
                try:
                    _send_item_card(api, chat_id, query)
                except Exception as e:
                    api.send_message(chat_id, f"⚠️ Ошибка карточки: {e}")
                return True
    return False
