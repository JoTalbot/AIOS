#!/usr/bin/env python3
"""
Фотокаталог склада.

  pull [--item "<название детали>"] [--n N]
      подтягивает N последних фото из DCIM/Camera телефона (adb pull),
      сохраняет в data/photos/, распознаёт через run_photo_recognition
      и (если --item) привязывает последнее фото к позиции склада.
  list — список позиций склада с фото.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PHOTOS = ROOT / "data" / "photos"
STATE = ROOT / "data" / "stock_photos_state.json"
ADB = "/usr/local/bin/aios-adb"


def _serial() -> str:
    try:
        d = json.loads((ROOT / "data" / "android_gateway" / "device.json").read_text(encoding="utf-8"))
        return str(d.get("serial") or "")
    except Exception:
        return ""


def _adb(args: list[str], timeout=60) -> subprocess.CompletedProcess:
    return subprocess.run([ADB, "-s", _serial()] + args, capture_output=True, text=True, timeout=timeout)


def _state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"pulled": []}


def pull(item: str | None = None, n: int = 1) -> dict:
    serial = _serial()
    if not serial:
        return {"status": "error", "error": "телефон не зарегистрирован"}
    st = _state()
    pulled = set(st.get("pulled") or [])
    ls = _adb(["shell", "ls -t /sdcard/DCIM/Camera 2>/dev/null"])
    names = [x.strip() for x in (ls.stdout or "").splitlines() if x.strip()][:20]
    fresh = [x for x in names if x not in pulled and x.lower().endswith((".jpg", ".jpeg", ".png"))][:n]
    if not fresh:
        return {"status": "ok", "pulled": [], "note": "новых фото в камере нет"}
    PHOTOS.mkdir(parents=True, exist_ok=True)
    import run_photo_recognition as rec
    out = []
    for name in fresh:
        local = PHOTOS / f"stock_{name}"
        r = _adb(["pull", f"/sdcard/DCIM/Camera/{name}", str(local)], timeout=120)
        if r.returncode != 0 or not local.exists():
            continue
        pulled.add(name)
        recog = rec.recognize(str(local))
        entry = {"file": str(local), "recognition": recog}
        if item:
            inv_p = ROOT / "data" / "inventory.json"
            inv = json.loads(inv_p.read_text(encoding="utf-8"))
            for it in inv:
                if str(it.get("name") or "").strip().casefold() == item.strip().casefold():
                    it["photo"] = str(local)
                    inv_p.write_text(json.dumps(inv, ensure_ascii=False, indent=2), encoding="utf-8")
                    entry["linked"] = it.get("name")
        out.append(entry)
    st["pulled"] = list(pulled)[-500:]
    STATE.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "pulled": out}


def list_catalog() -> dict:
    try:
        inv = json.loads((ROOT / "data" / "inventory.json").read_text(encoding="utf-8"))
    except Exception:
        inv = []
    rows = [{"name": i.get("name"), "qty": i.get("qty"), "price": i.get("price"),
             "photo": i.get("photo")} for i in inv]
    return {"status": "ok", "items": rows}


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "pull":
        item = None
        n = 1
        if "--item" in args:
            item = args[args.index("--item") + 1]
        if "--n" in args:
            n = int(args[args.index("--n") + 1])
        print(json.dumps(pull(item, n), ensure_ascii=False, indent=1))
        return 0
    print(json.dumps(list_catalog(), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
