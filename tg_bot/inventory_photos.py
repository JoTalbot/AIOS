"""Инвентарь по фото (выделено из run_telegram_bot.py).

Черновики товаров из фото в Telegram: подтверждение, редактирование цены/
названия/кол-ва/категории, создание на складе, публикация на OLX.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from tg_bot.common import _esc_tg
from tg_bot.state import (
    _inventory_drafts, _last_photo, _pending_add_photo,
    _pending_inventory_edits, _photo_albums,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

import random as _rnd


def _generate_draft_id(chat_id: int) -> str:
    return f"{chat_id}_{int(time.time()*1000)}_{_rnd.randint(1000,9999)}"

def _build_inventory_keyboard(draft_id: str, price, photos_len: int):
    try:
        price_int = int(float(price))
        price_label = f"{price_int} грн" if float(price).is_integer() else f"{price} грн"
    except:
        price_label = f"{price} грн"
    return {
        "inline_keyboard": [
            [
                {"text": f"✅ Подтвердить {price_label}", "callback_data": f"inv_confirm_{draft_id}"},
                {"text": "❌ Отмена", "callback_data": f"inv_cancel_{draft_id}"}
            ],
            [
                {"text": f"✅+📢 Склад+OLX ({price_label})", "callback_data": f"inv_confirm_olx_{draft_id}"},
                {"text": f"📢 Только OLX", "callback_data": f"inv_olx_{draft_id}"}
            ],
            [
                {"text": "✏️ Цена", "callback_data": f"inv_edit_price_{draft_id}"},
                {"text": "✏️ Название", "callback_data": f"inv_edit_name_{draft_id}"},
                {"text": "✏️ Кол-во", "callback_data": f"inv_edit_qty_{draft_id}"}
            ],
            [
                {"text": f"📸 +фото ({photos_len} шт)", "callback_data": f"inv_add_photo_{draft_id}"},
                {"text": "🏷 Категория", "callback_data": f"inv_edit_category_{draft_id}"}
            ]
        ]
    }

def _process_expired_albums(api):
    """Обработать альбомы Telegram, которые уже полностью пришли (>2.5 сек без новых фото)."""
    try:
        now = time.time()
        to_process = []
        for mg_id, album in list(_photo_albums.items()):
            if album.get("processed"):
                continue
            if now - album.get("ts", 0) > 2.5:
                to_process.append((mg_id, album))
        for mg_id, album in to_process:
            if len(album.get("photos", [])) == 0:
                _photo_albums.pop(mg_id, None)
                continue
            album["processed"] = True
            chat_id = album.get("chat_id")
            photos = album.get("photos", [])
            caption = album.get("caption") or ""
            # если этот альбом был для добавления фото к существующему черновику
            if chat_id in _pending_add_photo:
                draft_id = _pending_add_photo.get(chat_id)
                draft = _inventory_drafts.get(draft_id)
                if draft:
                    # добавляем фото к черновику
                    for p in photos:
                        if p not in draft["photos"]:
                            draft["photos"].append(p)
                    _last_photo[chat_id] = photos[-1]
                    api.send_message(chat_id,
                        f"📸 Добавил {len(photos)} фото к черновику «{draft.get('name')[:40]}» (теперь {len(draft['photos'])} шт).\nОтправьте ещё или нажмите ✅ Подтвердить.",
                        reply_markup=_build_inventory_keyboard(draft_id, draft.get('price',0), len(draft['photos'])))
                    _photo_albums.pop(mg_id, None)
                    continue
            # иначе создаём новый черновик из альбома
            _create_inventory_draft_and_ask_confirmation(api, chat_id, photos, caption)
            _photo_albums.pop(mg_id, None)
    except Exception as e:
        print(f"  [ALBUM PROCESS ERR] {e}")
        import traceback; traceback.print_exc()

def _create_inventory_draft_and_ask_confirmation(api, chat_id: int, photos: list, caption: str):
    """Создать черновик товара из фото(й) и отправить клавиатуру подтверждения."""
    if not photos:
        return
    first_photo = photos[0]
    # --- Vision ---
    recog = {"status":"error"}
    try:
        import subprocess as _sp2
        r = _sp2.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_photo_recognition.py"), first_photo],
                     capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT))
        out = (r.stdout or "").strip()
        for line in reversed(out.splitlines()):
            if "{" in line and "}" in line:
                try:
                    import json as _js
                    recog = _js.loads(line[line.find("{"):line.rfind("}")+1])
                    break
                except:
                    continue
        if recog.get("status")!="ok":
            try:
                import json as _js
                recog = _js.loads(out.splitlines()[-1])
            except:
                pass
    except Exception as e:
        recog = {"status":"error","error":str(e)}

    part_name = ""
    price_rec = 0
    condition = ""
    compatible = ""
    notes = ""
    provider = recog.get("provider","?")
    if recog.get("status")=="ok":
        part_name = (recog.get("part") or "").strip()
        try:
            price_rec = float(recog.get("price") or 0)
        except:
            price_rec = 0
        condition = recog.get("condition") or ""
        compatible = recog.get("compatible") or ""
        notes = recog.get("notes") or ""

    if caption:
        cap_clean = re.sub(r"^(добавь( на склад)?|создай товар|товар на склад|деталь|запчасть)\s*:?\s*", "", caption, flags=re.IGNORECASE).strip()
        if len(cap_clean)>=2:
            if not part_name or len(cap_clean) > len(part_name):
                part_name = cap_clean
            elif cap_clean.lower() not in part_name.lower():
                part_name = f"{part_name} {cap_clean}".strip()

    if not part_name:
        part_name = caption or "Автозапчасть с фото"

    qty = 1
    price = price_rec
    text_for_parse = caption or ""
    m_qty = re.search(r"(\d+)\s*шт", text_for_parse, re.IGNORECASE)
    if m_qty:
        try:
            qty = max(1, int(m_qty.group(1)))
        except:
            qty = 1
    m_price = re.search(r"(\d[\d\s.,]*)\s*(грн|uah|₴)", text_for_parse, re.IGNORECASE)
    if m_price:
        try:
            price = float(m_price.group(1).replace(" ","").replace(",","."))
        except:
            pass
    else:
        m_price2 = re.search(r"\b(\d{3,6})\b\s*$", text_for_parse)
        if m_price2 and price_rec==0:
            try:
                v=int(m_price2.group(1))
                if 100 <= v <= 50000:
                    price = float(v)
            except:
                pass

    category = "общее"
    try:
        from tg_bot.accounts import _llm_chat_direct as _llm_direct
        cat_prompt = f"Деталь: «{part_name}». Определи категорию из списка (двигатель, кузов, оптика, подвеска, тормоза, электрика, салон, трансмиссия, расходники, система охлаждения, другое) и верни ТОЛЬКО JSON {{\"category\":\"...\"}}."
        cat_resp = _llm_direct(cat_prompt)
        start = cat_resp.find("{")
        end = cat_resp.rfind("}")+1
        if start>=0 and end>start:
            import json as _js
            cj = _js.loads(cat_resp[start:end])
            category = (cj.get("category") or "общее").strip()[:40]
    except Exception:
        low = part_name.lower()
        if any(w in low for w in ("фара","фонарь","оптика","лампа","поворотник")):
            category="оптика"
        elif any(w in low for w in ("радиатор","охлаждение","термостат")):
            category="Система охлаждения"
        elif any(w in low for w in ("рессора","пружина","аморт","подвеска","рычаг","сайлент")):
            category="Подвеска"
        elif any(w in low for w in ("генератор","стартер","проводка","датчик")):
            category="Электрооборудование"
        elif any(w in low for w in ("бампер","капот","крыло","дверь","кузов")):
            category="Кузов"
        elif any(w in low for w in ("тормоз","колодка","диск тормоз")):
            category="Тормоза"
        elif any(w in low for w in ("кпп","коробка","трансмиссия")):
            category="Трансмиссия"

    draft_id = _generate_draft_id(chat_id)
    draft = {
        "draft_id": draft_id,
        "name": part_name[:120],
        "qty": qty,
        "price": price or 0,
        "category": category,
        "photos": photos,
        "condition": condition,
        "compatible": compatible,
        "notes": notes,
        "provider": provider,
        "caption": caption,
        "chat_id": chat_id,
        "ts": time.time(),
    }
    _inventory_drafts[draft_id] = draft

    kb = _build_inventory_keyboard(draft_id, draft["price"], len(photos))

    lines = [
        f"🔍 <b>Черновик товара (vision: {provider})</b>",
        f"📦 <b>{_esc_tg(draft['name'])}</b>",
        f"🔢 Кол-во: {qty} шт",
        f"💰 Цена: {int(price) if float(price).is_integer() else price} грн" + (f" (AI оценил {int(price_rec)} грн)" if price_rec and abs(float(price)-float(price_rec))>1 else ""),
        f"🏷 Категория: {_esc_tg(category)}",
    ]
    if condition:
        lines.append(f"📋 Состояние: {_esc_tg(condition)}")
    if compatible:
        lines.append(f"🚗 Совместимость: {_esc_tg(compatible)}")
    if notes:
        lines.append(f"📝 {_esc_tg(notes)}")
    lines.append(f"📸 Фото: {len(photos)} шт.")
    lines.append("")
    lines.append("Подтвердите или отредактируйте:")

    api.send_message(chat_id, "\n".join(lines), reply_markup=kb)

# === end helpers ===
