#!/usr/bin/env python3
"""
AIOS Shipments — клиенты и отправки Новой Почты (заказы на доставку).

  python run_shipments.py add_client "ФИО" "телефон" "город" "отделение"
  python run_shipments.py clients
  python run_shipments.py ship "деталь" "клиент_или_ФИО" "телефон" "город" "отделение"
  python run_shipments.py ships
  python run_shipments.py del_client "ФИО"
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLIENTS_FILE = ROOT / "data" / "clients.json"
SHIPS_FILE = ROOT / "data" / "shipments.json"


def _load(path: Path) -> list:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(path: Path, items: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def add_client(name: str, phone: str, city: str = "", warehouse: str = "") -> dict:
    clients = _load(CLIENTS_FILE)
    for c in clients:
        if c.get("name", "").lower() == name.lower():
            c.update({"phone": phone, "city": city, "warehouse": warehouse})
            _save(CLIENTS_FILE, clients)
            return {"status": "ok", "client": c, "msg": "клиент обновлён"}
    c = {"name": name, "phone": phone, "city": city, "warehouse": warehouse,
         "added": datetime.now().strftime("%Y-%m-%d %H:%M")}
    clients.append(c)
    _save(CLIENTS_FILE, clients)
    return {"status": "ok", "client": c, "msg": "клиент добавлен"}


def list_clients() -> dict:
    clients = _load(CLIENTS_FILE)
    return {"status": "ok", "clients": clients, "count": len(clients)}


def find_client(q: str) -> dict | None:
    ql = q.lower()
    for c in _load(CLIENTS_FILE):
        if ql in c.get("name", "").lower() or ql in c.get("phone", "").replace(" ", ""):
            return c
    return None


def ship(detail: str, client_ref: str, phone: str = "", city: str = "", warehouse: str = "") -> dict:
    """Записать заказ на отправку Новой Почтой."""
    client = None
    if client_ref:
        client = find_client(client_ref)
    if client:
        phone = phone or client.get("phone", "")
        city = city or client.get("city", "")
        warehouse = warehouse or client.get("warehouse", "")
        cname = client.get("name", client_ref)
    else:
        cname = client_ref
    if not (cname and phone):
        return {"status": "error", "error": "Нужны получатель и телефон. «добавь клиента: ФИО, телефон, город, отделение»"}
    ships = _load(SHIPS_FILE)
    ship_entry = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "detail": detail,
        "recipient": cname,
        "phone": phone,
        "city": city,
        "warehouse": warehouse,
        "status": "ждет отправки",
    }
    ships.insert(0, ship_entry)
    _save(SHIPS_FILE, ships)
    return {"status": "ok", "shipment": ship_entry, "total": len(ships)}


def list_ships(limit: int = 20) -> dict:
    ships = _load(SHIPS_FILE)
    return {"status": "ok", "shipments": ships[:limit], "count": len(ships[:limit])}


def del_client(name: str) -> dict:
    clients = _load(CLIENTS_FILE)
    before = len(clients)
    clients = [c for c in clients if c.get("name", "").lower() != name.lower()]
    _save(CLIENTS_FILE, clients)
    return {"status": "ok", "removed": before - len(clients)}


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "clients"
    if cmd == "add_client" and len(sys.argv) >= 4:
        print(json.dumps(add_client(sys.argv[2], sys.argv[3],
                                    sys.argv[4] if len(sys.argv) > 4 else "",
                                    sys.argv[5] if len(sys.argv) > 5 else ""), ensure_ascii=False))
    elif cmd == "clients":
        print(json.dumps(list_clients(), ensure_ascii=False))
    elif cmd == "ship" and len(sys.argv) >= 4:
        print(json.dumps(ship(sys.argv[2], sys.argv[3],
                              sys.argv[4] if len(sys.argv) > 4 else "",
                              sys.argv[5] if len(sys.argv) > 5 else "",
                              sys.argv[6] if len(sys.argv) > 6 else ""), ensure_ascii=False))
    elif cmd == "ships":
        print(json.dumps(list_ships(), ensure_ascii=False))
    elif cmd == "del_client" and len(sys.argv) >= 3:
        print(json.dumps(del_client(sys.argv[2]), ensure_ascii=False))
    else:
        print(json.dumps({"status": "error", "error": "add_client|clients|ship|ships|del_client"}))


if __name__ == "__main__":
    main()
