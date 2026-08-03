#!/usr/bin/env python3
"""
AIOS TTN — создание экспресс-накладной Новой Почты через официальный API.

  python run_ttn.py whoami                    # отправитель (проверка ключа)
  python run_ttn.py cities "<запрос>"          # поиск города
  python run_ttn.py warehouses "<город>" "<запрос>"  # поиск отделения
  python run_ttn.py create "<деталь>" <цена> "<ФИО>" <телефон> "<город>" "<отделение>" [--confirm]
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API_URL = "https://api.novaposhta.ua/v2.0/json/"


def _env(key: str) -> str:
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


def _api(model: str, method: str, props: dict) -> dict:
    key = _env("NOVAPOSHTA_API_KEY")
    if not key:
        return {"success": False, "errors": ["нет NOVAPOSHTA_API_KEY в .env"]}
    payload = json.dumps({"apiKey": key, "modelName": model,
                          "calledMethod": method, "methodProperties": props}).encode()
    req = urllib.request.Request(API_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def _sender_config() -> dict:
    """Данные отправителя (настраиваются один раз, data/np_sender.json)."""
    p = ROOT / "data" / "np_sender.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_sender(cfg: dict) -> None:
    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "np_sender.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_phone(p: str) -> str:
    digits = re.sub(r"\D", "", p or "")
    if digits.startswith("380"):
        return digits
    if digits.startswith("0"):
        return "38" + digits
    return "38" + digits if len(digits) == 9 else digits


def whoami() -> dict:
    r = _api("Counterparty", "getCounterparties",
             {"CounterpartyProperty": "Sender", "Page": "1"})
    if not r.get("success"):
        return {"status": "error", "error": str(r.get("errors", r))[:300]}
    data = r.get("data") or []
    if not data:
        return {"status": "error", "error": "Отправитель не найден в аккаунте API"}
    sender = data[0]
    ref = sender.get("Ref", "")
    ref_counterparty = sender.get("Counterparty", "")
    # ищем адрес отправки по контрагенту
    addr_ref = ""
    addr_desc = ""
    r2 = _api("Counterparty", "getCounterpartyAddresses", {"Ref": ref_counterparty or ref})
    addrs = r2.get("data") or [] if r2.get("success") else []
    if addrs:
        addr_ref = addrs[0].get("Ref", "")
        addr_desc = addrs[0].get("Description", "")
    # контактные лица отправителя — ищем по Ref (ref контрагента-отправителя),
    # НЕ по Counterparty (там «Counterparty not found»).
    contact_ref = ""
    contact_desc = ""
    r3 = _api("Counterparty", "getCounterpartyContactPersons", {"Ref": ref})
    cps = r3.get("data") or [] if r3.get("success") else []
    if cps:
        # берём первого (Гончаренко Костянтин)
        contact_ref = cps[0].get("Ref", "")
        contact_desc = cps[0].get("Description", "")
    ready = bool(ref and addr_ref and contact_ref)
    return {"status": "ok", "sender": {
        "description": sender.get("Description"),
        "ref": ref,
        "ref_contact": ref,
        "ref_counterparty": ref_counterparty,
        "contact_ref": contact_ref,
        "contact_desc": contact_desc,
        "phones": sender.get("Phones", ""),
        "address": addr_desc,
        "address_ref": addr_ref,
        "ready": ready,
    }}


def cities(query: str, limit: int = 5) -> dict:
    r = _api("Address", "getCities", {"FindByString": query, "Limit": str(limit)})
    if not r.get("success"):
        return {"status": "error", "error": str(r.get("errors", r))[:300]}
    return {"status": "ok", "cities": [
        {"name": c.get("Description"), "ref": c.get("Ref"), "area": c.get("AreaDescription")}
        for c in (r.get("data") or [])]}


def warehouses(city: str, query: str = "", limit: int = 10) -> dict:
    cr = _api("Address", "getCities", {"FindByString": city, "Limit": "1"})
    if not cr.get("success") or not cr.get("data"):
        return {"status": "error", "error": f"Город «{city}» не найден"}
    city_ref = cr["data"][0]["Ref"]
    props = {"CityRef": city_ref, "Limit": str(limit)}
    if query:
        props["FindByString"] = query
    r = _api("AddressGeneral", "getWarehouses", props)
    if not r.get("success"):
        return {"status": "error", "error": str(r.get("errors", r))[:300]}
    return {"status": "ok", "city": city, "warehouses": [
        {"name": w.get("Description"), "ref": w.get("Ref")}
        for w in (r.get("data") or [])]}


def _find_recipient(phone: str) -> dict | None:
    """Найти получателя в адресной книге по телефону."""
    r = _api("Counterparty", "getCounterparties",
             {"CounterpartyProperty": "Recipient", "FindByString": phone[-9:], "Page": "1"})
    if r.get("success") and r.get("data"):
        c = r["data"][0]
        return {"ref_counterparty": c.get("Counterparty") or c.get("Ref"),
                "ref_contact": c.get("Ref"),
                "description": c.get("Description"),
                "phones": c.get("Phones")}
    return None


def _create_recipient(name: str, phone: str) -> dict | None:
    """Создать получателя в адресной книге."""
    parts = name.split()
    first = parts[0] if parts else name
    last = parts[1] if len(parts) > 1 else ""
    middle = parts[2] if len(parts) > 2 else ""
    r = _api("Counterparty", "save", {
        "CounterpartyProperty": "Recipient",
        "CounterpartyType": "PrivatePerson",
        "FirstName": first, "LastName": last, "MiddleName": middle,
        "Phone": _normalize_phone(phone),
    })
    if r.get("success") and r.get("data"):
        d = r["data"][0]
        return {"ref_counterparty": d.get("Ref"), "ref_contact": d.get("ContactPerson", {}).get("data", [{}])[0].get("Ref") if d.get("ContactPerson") else d.get("Ref"),
                "description": d.get("Description")}
    return None


def create_ttn(detail: str, cost: str, recipient_name: str, recipient_phone: str,
               recipient_city: str, recipient_wh: str, confirm: bool = False) -> dict:
    if not confirm:
        return {"status": "need_confirm", "action": "ttn_create",
                "detail": detail, "cost": cost, "recipient": recipient_name,
                "phone": recipient_phone, "city": recipient_city, "warehouse": recipient_wh}

    cfg = _sender_config()
    sender_phone = cfg.get("sender_phone") or "380959052288"
    sender_city = cfg.get("sender_city") or "Кропивницький"
    sender_wh = cfg.get("sender_warehouse") or ""

    # 1) отправитель
    sw = whoami()
    if sw.get("status") != "ok":
        return sw
    sender = sw["sender"]
    # Sender (контрагент-отправитель) = Ref отправителя из getCounterparties(Sender);
    # ContactSender = контактное лицо.
    sender_ref = sender["ref"] or sender["ref_counterparty"]
    sender_contact = sender.get("contact_ref") or sender["ref_contact"] or ""
    # Адрес отправки: из конфига (если есть), затем из API, иначе первое отделение города.
    cfg_addr_ref = cfg.get("sender_addr_ref") or ""
    if not sender_contact:
        return {"status": "error",
                "error": "Не найдено контактное лицо отправителя в кабинете Новой Почты "
                         "(Настройки → Мои данные → контактное лицо)."}
    if cfg_addr_ref:
        sender_addr_ref = cfg_addr_ref
    elif not sender.get("address_ref"):
        whs = warehouses(sender_city, sender_wh or "")
        if whs.get("status") != "ok" or not whs.get("warehouses"):
            return {"status": "error", "error": f"Не найдено отделение отправки в {sender_city}"}
        if sender_wh:
            w = next((x for x in whs["warehouses"] if sender_wh.lower() in x["name"].lower()), whs["warehouses"][0])
        else:
            w = whs["warehouses"][0]
        sender_addr_ref = w["ref"]
        _save_sender({**cfg, "sender_city": sender_city,
                      "sender_warehouse": w["name"], "sender_addr_ref": sender_addr_ref})
    else:
        sender_addr_ref = sender["address_ref"]

    # 3) город получателя
    cr = _api("Address", "getCities", {"FindByString": recipient_city, "Limit": "1"})
    if not cr.get("success") or not cr.get("data"):
        return {"status": "error", "error": f"Город получателя «{recipient_city}» не найден"}
    city_rec_ref = cr["data"][0]["Ref"]
    # 4) отделение получателя
    wr = _api("AddressGeneral", "getWarehouses",
              {"CityRef": city_rec_ref, "FindByString": recipient_wh, "Limit": "5"})
    whs_rec = wr.get("data") or [] if wr.get("success") else []
    if not whs_rec:
        return {"status": "error", "error": f"Отделение «{recipient_wh}» в {recipient_city} не найдено"}
    w_rec = next((x for x in whs_rec if recipient_wh.lower() in (x.get("Description") or "").lower()), whs_rec[0])
    # 5) получатель
    rec = _find_recipient(recipient_phone)
    if not rec:
        rec = _create_recipient(recipient_name, recipient_phone)
    if not rec:
        return {"status": "error", "error": "Не удалось создать/найти получателя"}

    # 6) создание накладной
    dt = (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
    props = {
        "PayerType": "Sender",
        "PaymentMethod": "Cash",
        "DateTime": dt,
        "CargoType": "Cargo",
        "Weight": "5",
        "ServiceType": "WarehouseWarehouse",
        "SeatsAmount": "1",
        "Description": detail[:300],
        "Cost": str(cost),
        "CitySender": sender_city_ref(),
        "Sender": sender_ref,
        "SenderAddress": sender_addr_ref,
        "SendersPhone": _normalize_phone(sender_phone),
        "ContactSender": sender_contact,
        "CityRecipient": city_rec_ref,
        "Recipient": rec["ref_counterparty"],
        "RecipientAddress": w_rec["Ref"],
        "ContactRecipient": rec.get("ref_contact") or rec["ref_counterparty"],
        "RecipientsPhone": _normalize_phone(recipient_phone),
    }
    r = _api("InternetDocument", "save", props)
    if not r.get("success"):
        return {"status": "error", "error": str(r.get("errors", r))[:400]}
    d = r["data"][0] if r.get("data") else {}
    return {"status": "ok", "ttn": d.get("IntDocNumber") or d.get("Number", ""),
            "ref": d.get("Ref", ""), "cost": cost,
            "recipient": recipient_name, "detail": detail}


def sender_city_ref() -> str:
    """Ref города отправителя (Кропивницький) — кэшируется."""
    cfg = _sender_config()
    if cfg.get("sender_city_ref"):
        return cfg["sender_city_ref"]
    r = _api("Address", "getCities", {"FindByString": "Кропивницький", "Limit": "1"})
    if r.get("success") and r.get("data"):
        ref = r["data"][0]["Ref"]
        _save_sender({**cfg, "sender_city_ref": ref})
        return ref
    return ""


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "whoami"
    if cmd == "whoami":
        print(json.dumps(whoami(), ensure_ascii=False))
    elif cmd == "cities" and len(sys.argv) >= 3:
        print(json.dumps(cities(sys.argv[2]), ensure_ascii=False))
    elif cmd == "warehouses" and len(sys.argv) >= 3:
        print(json.dumps(warehouses(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ""),
                         ensure_ascii=False))
    elif cmd == "create" and len(sys.argv) >= 7:
        confirm = "--confirm" in sys.argv
        print(json.dumps(create_ttn(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5],
                                    sys.argv[6], sys.argv[7] if len(sys.argv) > 7 else "",
                                    confirm), ensure_ascii=False))
    else:
        print(json.dumps({"status": "error",
                          "error": "whoami|cities|warehouses|create"}))


if __name__ == "__main__":
    main()
