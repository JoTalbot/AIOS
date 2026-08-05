#!/usr/bin/env python3
"""
Хранилище карт владельца (data/.cards_vault.json, 0600, вне git).

Напоминание реквизитов — только в доверенных каналах:
в чате Arena или локально на сервере (НИКОГДА в TG/брифинги/логи).

  python run_cards_vault.py list            — список карт (маскированно)
  python run_cards_vault.py show <маска>    — полные реквизиты (номер, exp, cvv)
  python run_cards_vault.py add '<json>'    — добавить/обновить карту
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VAULT = ROOT / "data" / ".cards_vault.json"


def load() -> dict:
    try:
        return json.loads(VAULT.read_text(encoding="utf-8"))
    except Exception:
        return {"banks": []}


def save(data: dict) -> None:
    VAULT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    VAULT.chmod(0o600)


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    data = load()
    if cmd == "list":
        for bank in data.get("banks", []):
            print(bank.get("bank"))
            for c in bank.get("cards", []):
                print(f"  {c.get('name', '?')} | {c.get('number_masked', '?')} | "
                      f"exp {c.get('exp', '?')} | баланс {c.get('balance', '?')}")
        return 0
    if cmd == "show":
        mask = (sys.argv[2] if len(sys.argv) > 2 else "").replace(" ", "")
        for bank in data.get("banks", []):
            for c in bank.get("cards", []):
                if mask and mask in str(c.get("number_full", c.get("number_masked", ""))).replace(" ", ""):
                    print(json.dumps({**c, "bank": bank.get("bank")}, ensure_ascii=False, indent=1))
                    return 0
        print("не найдено")
        return 1
    if cmd == "add":
        card = json.loads(sys.argv[2])
        bank_name = card.pop("bank", "?")
        bank = next((b for b in data["banks"] if b.get("bank") == bank_name), None)
        if bank is None:
            bank = {"bank": bank_name, "cards": []}
            data["banks"].append(bank)
        masked = card.get("number_masked") or ("** " + str(card.get("number_full", ""))[-4:])
        existing = next((c for c in bank["cards"]
                         if c.get("number_masked") == masked), None)
        if existing:
            existing.update(card)
        else:
            bank["cards"].append(card)
        save(data)
        print("saved", masked)
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
