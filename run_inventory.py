#!/usr/bin/env python3
"""
AIOS Inventory — учёт запчастей на складе авторазборки.

  python run_inventory.py add "<название>" <кол-во> <цена> [категория]
  python run_inventory.py list [категория]
  python run_inventory.py search <запрос>
  python run_inventory.py take "<название>" <кол-во>   (списать свободный остаток)
  python run_inventory.py stats

Для продаж с ТТН доступны внутренние операции reserve/commit_reservation:
резерв уменьшает доступный остаток, но не физический ``qty``; фактическое
списание происходит только после передачи товара перевозчику.

Данные: data/inventory.json
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "inventory.json"
_ACTIVE_RESERVATION_STATES = {"reserved", "awaiting_shipment"}


def _path(data_path: Path | str | None = None) -> Path:
    return Path(data_path) if data_path is not None else DATA


def _load(data_path: Path | str | None = None) -> list[dict]:
    try:
        value = json.loads(_path(data_path).read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _save(items: list[dict], data_path: Path | str | None = None) -> None:
    target = _path(data_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, target)


def _find(items: list[dict], name: str) -> dict | None:
    """Найти по имени: сначала точное, затем частичное совпадение."""
    name_l = (name or "").strip().casefold()
    if not name_l:
        return None
    for it in items:
        if str(it.get("name") or "").casefold() == name_l:
            return it
    for it in items:
        item_name = str(it.get("name") or "").casefold()
        if name_l in item_name:
            return it
    return None


def _reservations(item: dict) -> list[dict]:
    value = item.get("reservations")
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def reserved_qty(item: dict) -> int:
    """Количество, обещанное покупателям, но ещё физически лежащее на складе."""
    total = 0
    for reservation in _reservations(item):
        if reservation.get("status") in _ACTIVE_RESERVATION_STATES:
            try:
                total += max(0, int(reservation.get("qty") or 0))
            except (TypeError, ValueError):
                continue
    return total


def available_qty(item: dict) -> int:
    try:
        qty = max(0, int(item.get("qty") or 0))
    except (TypeError, ValueError):
        qty = 0
    return max(0, qty - reserved_qty(item))


def _refresh_reservation_summary(item: dict) -> None:
    reserved = reserved_qty(item)
    item["reserved_qty"] = reserved
    if reserved:
        # Товар уже продан конкретному покупателю, но физически ещё лежит на
        # складе до передачи перевозчику. Отдельное поле не даёт смешать это
        # состояние с обычным «в наличии».
        item["sale_state"] = "sold_awaiting_shipment"
        item["stock_status"] = "reserved" if available_qty(item) == 0 else "partially_reserved"
    else:
        item.pop("sale_state", None)
        if int(item.get("qty") or 0) > 0:
            item["stock_status"] = "in_stock"
        else:
            item["stock_status"] = "out_of_stock"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def add(name: str, qty: int, price: float, category: str = "", photo: str = "",
        photos: list[str] | None = None, data_path: Path | str | None = None) -> dict:
    """Добавить деталь. Поддержка мульти-фото: photo (один путь) и photos (список)."""
    items = _load(data_path)
    it = _find(items, name)
    src_list: list[str] = []
    if photos:
        src_list.extend([p for p in photos if isinstance(p, str)])
    if photo and isinstance(photo, str):
        if "," in photo:
            src_list.extend([x.strip() for x in photo.split(",") if x.strip()])
        elif photo not in src_list:
            src_list.append(photo)
    saved_photos = _save_photos(src_list, name, data_path) if src_list else []
    photo_saved = saved_photos[0] if saved_photos else ""
    if it:
        it["qty"] = int(it.get("qty", 0)) + int(qty)
        if price:
            it["price"] = float(price)
        if category:
            it["category"] = category
        existing_photos = []
        if isinstance(it.get("photos"), list):
            existing_photos = [p for p in it["photos"] if isinstance(p, str)]
        elif it.get("photo"):
            existing_photos = [it["photo"]]
        for p in saved_photos:
            if p not in existing_photos:
                existing_photos.append(p)
        if existing_photos:
            it["photos"] = existing_photos
            it["photo"] = existing_photos[0]
        elif photo_saved:
            it["photo"] = photo_saved
        _refresh_reservation_summary(it)
        msg = f"добавлено (итого {it['qty']})"
    else:
        it = {
            "name": name,
            "qty": int(qty),
            "price": float(price or 0),
            "category": category or "общее",
            "added": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "reservations": [],
        }
        if saved_photos:
            it["photos"] = saved_photos
            it["photo"] = saved_photos[0]
        elif photo_saved:
            it["photo"] = photo_saved
        _refresh_reservation_summary(it)
        items.append(it)
        msg = "новая деталь"
    _save(items, data_path)
    return {"status": "ok", "item": it, "msg": msg, "total": len(items), "photos": saved_photos if 'saved_photos' in locals() else []}


def _save_photo(src: str, name: str, data_path: Path | str | None = None, suffix: str = "") -> str:
    """Сохранить фото детали в data/photos/ и вернуть путь. Поддержка мульти-фото через suffix."""
    import re as _re
    import shutil
    import time as _time

    photos_dir = _path(data_path).parent / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    slug = _re.sub(r"[^\w\-а-яА-ЯіїєґІЇЄҐ ]", "", name).strip().replace(" ", "_")[:50] or "detail"
    ext = Path(src).suffix or ".jpg"
    if suffix:
        dest = photos_dir / f"{slug}_{suffix}{ext}"
    else:
        dest = photos_dir / f"{slug}{ext}"
        if dest.exists():
            dest = photos_dir / f"{slug}_{int(_time.time())}{ext}"
    try:
        shutil.copyfile(src, dest)
        return str(dest)
    except Exception:
        return ""


def _save_photos(src_list: list[str], name: str, data_path: Path | str | None = None) -> list[str]:
    """Сохранить несколько фото и вернуть список путей."""
    saved = []
    for idx, src in enumerate(src_list or []):
        if src and os.path.exists(src):
            suf = f"{idx+1}" if len(src_list) > 1 else ""
            p = _save_photo(src, name, data_path, suffix=suf)
            if p and p not in saved:
                saved.append(p)
    return saved


def reserve(name: str, qty: int = 1, sale_id: str = "", ttn: str = "",
            data_path: Path | str | None = None) -> dict:
    """Зарезервировать товар после создания ТТН, не списывая физический остаток."""
    qty = int(qty or 1)
    if qty <= 0:
        return {"status": "error", "error": "Количество резерва должно быть > 0"}
    if not sale_id:
        return {"status": "error", "error": "Для резерва нужен sale_id"}
    items = _load(data_path)
    it = _find(items, name)
    if not it:
        return {"status": "error", "error": f"«{name}» нет на складе"}
    rows = _reservations(it)
    previous = next((r for r in rows if str(r.get("sale_id") or "") == sale_id), None)
    if previous and previous.get("status") in _ACTIVE_RESERVATION_STATES:
        _refresh_reservation_summary(it)
        _save(items, data_path)
        return {"status": "ok", "item": it, "reservation": previous, "idempotent": True}
    available = available_qty(it)
    if available < qty:
        return {
            "status": "error",
            "error": f"Свободно только {available} шт «{it.get('name')}» (зарезервировано: {reserved_qty(it)})",
        }
    reservation = {
        "sale_id": sale_id,
        "ttn": str(ttn or ""),
        "qty": qty,
        "status": "reserved",
        "created_at": _now(),
    }
    rows.append(reservation)
    it["reservations"] = rows
    _refresh_reservation_summary(it)
    _save(items, data_path)
    return {"status": "ok", "item": it, "reservation": reservation,
            "msg": f"зарезервировано {qty} шт"}


def commit_reservation(sale_id: str, name: str = "", data_path: Path | str | None = None) -> dict:
    """Списать физический остаток при подтверждённой отправке товара."""
    if not sale_id:
        return {"status": "error", "error": "Нужен sale_id"}
    items = _load(data_path)
    target: tuple[dict, dict] | None = None
    for item in items:
        for reservation in _reservations(item):
            if str(reservation.get("sale_id") or "") == sale_id:
                target = (item, reservation)
                break
        if target:
            break
    if not target:
        return {"status": "error", "error": f"Резерв для сделки {sale_id} не найден"}
    it, reservation = target
    if reservation.get("status") == "shipped":
        return {"status": "ok", "item": it, "reservation": reservation, "idempotent": True}
    if reservation.get("status") not in _ACTIVE_RESERVATION_STATES:
        return {"status": "error", "error": f"Резерв уже имеет статус {reservation.get('status')}"}
    qty = max(1, int(reservation.get("qty") or 1))
    physical = int(it.get("qty") or 0)
    if physical < qty:
        return {"status": "error", "error": f"На складе физически только {physical} шт «{it.get('name')}»"}
    it["qty"] = physical - qty
    reservation.update({"status": "shipped", "committed_at": _now()})
    _refresh_reservation_summary(it)
    _save(items, data_path)
    return {"status": "ok", "item": it, "reservation": reservation,
            "msg": f"списано {qty} шт после отправки"}


def release_reservation(sale_id: str, data_path: Path | str | None = None) -> dict:
    """Освободить товар при отмене до физической отправки."""
    items = _load(data_path)
    for it in items:
        for reservation in _reservations(it):
            if str(reservation.get("sale_id") or "") == sale_id:
                if reservation.get("status") in _ACTIVE_RESERVATION_STATES:
                    reservation.update({"status": "released", "released_at": _now()})
                    _refresh_reservation_summary(it)
                    _save(items, data_path)
                    return {"status": "ok", "item": it, "reservation": reservation}
                return {"status": "ok", "item": it, "reservation": reservation, "idempotent": True}
    return {"status": "error", "error": f"Резерв для сделки {sale_id} не найден"}


def restore_return(sale_id: str, name: str, qty: int = 1, price: float = 0,
                   data_path: Path | str | None = None) -> dict:
    """Вернуть физически полученный возврат в остатки, идемпотентно по sale_id."""
    qty = max(1, int(qty or 1))
    items = _load(data_path)
    it = _find(items, name)
    if it is None:
        it = {
            "name": name,
            "qty": 0,
            "price": float(price or 0),
            "category": "возвраты",
            "added": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "reservations": [],
        }
        items.append(it)
    receipts = it.get("return_receipts") if isinstance(it.get("return_receipts"), list) else []
    existing = next((x for x in receipts if isinstance(x, dict) and x.get("sale_id") == sale_id), None)
    if existing:
        return {"status": "ok", "item": it, "receipt": existing, "idempotent": True}
    it["qty"] = int(it.get("qty") or 0) + qty
    if not it.get("price") and price:
        it["price"] = float(price)
    receipt = {"sale_id": sale_id, "qty": qty, "received_at": _now()}
    receipts.append(receipt)
    it["return_receipts"] = receipts
    _refresh_reservation_summary(it)
    _save(items, data_path)
    return {"status": "ok", "item": it, "receipt": receipt,
            "msg": f"возврат добавлен: {qty} шт"}


def take(name: str, qty: int = 1, data_path: Path | str | None = None) -> dict:
    """Списать только свободный остаток; товар, обещанный по ТТН, не трогаем."""
    qty = int(qty or 1)
    items = _load(data_path)
    it = _find(items, name)
    if not it:
        return {"status": "error", "error": f"«{name}» нет на складе"}
    available = available_qty(it)
    if available < qty:
        suffix = f" (из них {reserved_qty(it)} шт зарезервировано)" if reserved_qty(it) else ""
        return {"status": "error", "error": f"Свободно только {available} шт «{it['name']}»{suffix}"}
    it["qty"] = int(it.get("qty") or 0) - qty
    _refresh_reservation_summary(it)
    _save(items, data_path)
    return {"status": "ok", "item": it, "msg": f"списано {qty} шт"}


def search(query: str, data_path: Path | str | None = None) -> dict:
    items = _load(data_path)
    q = (query or "").casefold()
    found = [it for it in items if q in str(it.get("name") or "").casefold()
             or q in str(it.get("category") or "").casefold()]
    return {"status": "ok", "items": [_view(it) for it in found], "count": len(found)}


def _view(item: dict) -> dict:
    view = dict(item)
    view["reserved_qty"] = reserved_qty(item)
    view["available_qty"] = available_qty(item)
    if view["reserved_qty"]:
        view["stock_status"] = "reserved" if view["available_qty"] == 0 else "partially_reserved"
    elif int(view.get("qty") or 0) > 0:
        view["stock_status"] = "in_stock"
    else:
        view["stock_status"] = "out_of_stock"
    return view


def listing(category: str | None = None, data_path: Path | str | None = None) -> dict:
    items = _load(data_path)
    if category:
        items = [it for it in items if str(it.get("category") or "").casefold() == category.casefold()]
    views = [_view(it) for it in items]
    views = sorted(views, key=lambda x: x.get("available_qty", 0) == 0)  # пустые/резерв в конец
    return {"status": "ok", "items": views, "count": len(views)}


def stats(data_path: Path | str | None = None) -> dict:
    items = _load(data_path)
    total_qty = sum(max(0, int(it.get("qty") or 0)) for it in items)
    total_reserved = sum(reserved_qty(it) for it in items)
    total_available = sum(available_qty(it) for it in items)
    total_value = sum(available_qty(it) * float(it.get("price") or 0) for it in items)
    zero = [str(it.get("name") or "") for it in items if available_qty(it) == 0]
    return {
        "status": "ok", "items_count": len(items), "total_qty": total_qty,
        "available_qty": total_available, "reserved_qty": total_reserved,
        "total_value": round(total_value, 2), "out_of_stock": zero,
    }


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "add" and len(sys.argv) >= 4:
        args = list(sys.argv[2:])
        photo = ""
        if "--photo" in args:
            index = args.index("--photo")
            if index + 1 < len(args):
                photo = args[index + 1]
                args = args[:index] + args[index + 2:]
        name = args[0]
        try:
            qty = int(args[1])
            price = float(args[2]) if len(args) > 2 else 0
        except (IndexError, ValueError):
            print(json.dumps({"status": "error", "error": "кол-во и цена"}, ensure_ascii=False)); return
        category = args[3] if len(args) > 3 else ""
        print(json.dumps(add(name, qty, price, category, photo), ensure_ascii=False))
    elif cmd == "take" and len(sys.argv) >= 3:
        qty = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        print(json.dumps(take(sys.argv[2], qty), ensure_ascii=False))
    elif cmd == "reserve" and len(sys.argv) >= 4:
        qty = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        print(json.dumps(reserve(sys.argv[2], qty=qty, sale_id=sys.argv[3]), ensure_ascii=False))
    elif cmd == "commit_reservation" and len(sys.argv) >= 3:
        print(json.dumps(commit_reservation(sys.argv[2]), ensure_ascii=False))
    elif cmd == "search" and len(sys.argv) >= 3:
        print(json.dumps(search(sys.argv[2]), ensure_ascii=False))
    elif cmd == "list":
        category = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(listing(category), ensure_ascii=False))
    elif cmd == "stats":
        print(json.dumps(stats(), ensure_ascii=False))
    else:
        print(json.dumps({"status": "error", "error": "add|take|reserve|commit_reservation|search|list|stats"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
