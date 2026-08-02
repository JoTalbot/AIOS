#!/usr/bin/env python3
"""
AIOS Export — экспорт данных в Excel (openpyxl) / CSV.
  python run_export.py olx [query]         — объявления OLX из БД
  python run_export.py gmail [N]           — последние N писем
  python run_export.py contacts [N]        — Google контакты
Выводит путь к файлу (JSON).
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Font  # noqa: E402

OUT = ROOT / "data" / "exports"


def _run_ac(args, timeout=170) -> dict:
    py = "/opt/aios/.venv/bin/python"
    needs_x = not (len(args) >= 2 and args[0] == "google" and args[1] in ("gmail_list", "gmail_send", "gmail_search", "open"))
    cmd = (["xvfb-run", "-a", "-s", "-screen 0 1440x900x24", py, str(ROOT / "run_account_control.py")] + args) \
        if needs_x else ([py, str(ROOT / "run_account_control.py")] + args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
        out = (r.stdout or "").strip()
        start = out.find("{")
        return json.loads(out[start:]) if start >= 0 else {"status": "error", "error": out[-300:]}
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "timeout"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


def _xl(path: Path, headers: list, rows: list) -> str:
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True)
    for row in rows:
        ws.append(row)
    wb.save(path)
    return str(path)


def export_olx(query: str | None = None) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(ROOT / "data" / "olx_http.sqlite"))
    if query:
        rows = conn.execute(
            "SELECT url, title, price_value, price_currency, city, region, description, category "
            "FROM ads WHERE query LIKE ? AND active = 1 ORDER BY collected_at DESC LIMIT 500",
            (f"%{query}%",)).fetchall()
    else:
        rows = conn.execute(
            "SELECT url, title, price_value, price_currency, city, region, description, category "
            "FROM ads WHERE active = 1 ORDER BY collected_at DESC LIMIT 500").fetchall()
    conn.close()
    path = OUT / f"olx_{query or 'all'}_{int(time.time())}.xlsx"
    xl = _xl(path, ["URL", "Название", "Цена", "Валюта", "Город", "Регион", "Описание", "Категория"], rows)
    return {"status": "ok", "file": xl, "rows": len(rows)}


def export_gmail(n: int = 50) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    import run_account_control as rac
    g = rac.gmail_list(n)
    if g.get("status") != "ok":
        return {"status": "error", "error": g.get("error", "?")}
    rows = []
    for e in g.get("emails", []):
        rows.append([e.get("date", ""), e.get("from", ""), e.get("subject", ""),
                     e.get("snippet", "")[:150], "🔴" if e.get("unread") else ""])
    path = OUT / f"gmail_{int(time.time())}.xlsx"
    xl = _xl(path, ["Дата", "От", "Тема", "Сниппет", "Непрочитано"], rows)
    return {"status": "ok", "file": xl, "rows": len(rows)}


def export_finance(days: int = 30) -> dict:
    """Экспорт финансов в CSV (для Google Sheets)."""
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        items = json.loads((ROOT / "data" / "finance.json").read_text(encoding="utf-8"))
    except Exception:
        items = []
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = [x for x in items if x["date"][:10] >= since]
    path = OUT / f"finance_{int(time.time())}.csv"
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write("Дата;Тип;Сумма;Описание\n")
        for x in recent:
            f.write(f"{x['date']};{'продажа' if x['kind']=='sale' else 'расход'};{x['amount']};{x['desc']}\n")
    return {"status": "ok", "file": str(path), "rows": len(recent)}


def export_inventory() -> dict:
    """Экспорт склада в CSV (для Google Sheets)."""
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        items = json.loads((ROOT / "data" / "inventory.json").read_text(encoding="utf-8"))
    except Exception:
        items = []
    path = OUT / f"inventory_{int(time.time())}.csv"
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write("Название;Кол-во;Цена;Категория\n")
        for x in items:
            f.write(f"{x.get('name','')};{x.get('qty',0)};{x.get('price',0)};{x.get('category','')}\n")
    return {"status": "ok", "file": str(path), "rows": len(items)}


def export_contacts(n: int = 200) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    res = _run_ac(["google", "contacts_list", "--limit", str(n)])
    if res.get("status") != "ok":
        return {"status": "error", "error": res.get("error", "?")}
    rows = []
    for c in res.get("contacts", []):
        rows.append([c.get("name", ""), c.get("email", "")])
    path = OUT / f"contacts_{int(time.time())}.xlsx"
    xl = _xl(path, ["Имя", "Email"], rows)
    return {"status": "ok", "file": xl, "rows": len(rows)}


def main() -> None:
    what = sys.argv[1] if len(sys.argv) > 1 else "olx"
    try:
        if what == "olx":
            q = sys.argv[2] if len(sys.argv) > 2 else None
            print(json.dumps(export_olx(q), ensure_ascii=False))
        elif what == "gmail":
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            print(json.dumps(export_gmail(n), ensure_ascii=False))
        elif what == "contacts":
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 200
            print(json.dumps(export_contacts(n), ensure_ascii=False))
        elif what == "finance":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            print(json.dumps(export_finance(days), ensure_ascii=False))
        elif what == "inventory":
            print(json.dumps(export_inventory(), ensure_ascii=False))
        else:
            print(json.dumps({"status": "error", "error": f"Неизвестно: {what}"}))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)[:300]}))


if __name__ == "__main__":
    main()
