#!/usr/bin/env python3
"""Скачивание уникальных реальных фото деталей из OLX-объявлений (БД коллектора)
для позиций склада без собственных уникальных фото."""
import json
import re
import sqlite3
import urllib.request
from pathlib import Path

ROOT = Path("/root/AIOS")
INVENTORY = ROOT / "data" / "inventory.json"
DB = ROOT / "data" / "olx_http.sqlite"
OUTDIR = ROOT / "data" / "photos" / "unique"
OUTDIR.mkdir(parents=True, exist_ok=True)

_STOP = {
    "авторазборк", "разбор", "автозапчастин", "запчастин", "б/у", "бу",
    "продам", "купить", "украин", "київ", "киев", "olx", "новая", "новый",
    "в", "сборе", "с", "и", "на", "для", "задний", "передний", "задняя",
    "передняя", "внутренние", "наружные", "за", "от", "б/у",
}


def _tokens(name: str, compat: str = "") -> list[str]:
    text = f"{name} {compat}".lower()
    for w in ("в", "сборе", "с", "и", "на", "для", "задний", "передний",
              "задняя", "передняя", "внутренние", "наружные", "за", "от", "б/у"):
        text = text.replace(f" {w} ", " ")
    words = re.findall(r"[а-яёa-z0-9]{3,}", text)
    return [w for w in words if w not in _STOP][:6]


def _match(title: str, tokens: list[str], required: int = 2) -> bool:
    t = (title or "").lower()
    return sum(1 for tok in tokens if tok in t) >= required


def _download(url: str, dest: Path) -> bool:
    """Скачать фото по URL (подставить размер)."""
    try:
        # OLX CDN: заменяем {width}x{height} на реальный размер
        u = url.replace("{width}", "600").replace("{height}", "450")
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        if len(data) < 2000:
            return False
        dest.write_bytes(data)
        return True
    except Exception:
        return False


def main() -> None:
    items = json.loads(INVENTORY.read_text(encoding="utf-8"))
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT title, photos_json FROM ads WHERE active=1 AND photos_json IS NOT NULL"
    ).fetchall()
    con.close()

    # индекс: токены -> объявления
    fetched = 0
    skipped = 0
    for it in items:
        name = it.get("name", "")
        photos = it.get("photos") or ([it["photo"]] if it.get("photo") else [])
        real = [p for p in photos if Path(p).exists()]
        if real and not any("ws_cat" in str(p) for p in real):
            skipped += 1  # уже есть собственное фото
            continue
        tokens = _tokens(name, it.get("compatibility", ""))
        if not tokens:
            continue
        # ищем лучшее совпадение
        best = None
        best_hits = 0
        for title, ph_json in rows:
            hits = sum(1 for tok in tokens if tok in (title or "").lower())
            if hits >= 2 and hits > best_hits:
                best = ph_json
                best_hits = hits
        if not best:
            skipped += 1
            continue
        try:
            urls = json.loads(best)
        except Exception:
            urls = []
        if not urls:
            skipped += 1
            continue
        # имя файла: ws_u_<индекс>.jpg
        idx = items.index(it) + 1
        dest = OUTDIR / f"ws_u_{idx:03d}.jpg"
        ok = False
        for u in urls[:3]:
            if _download(u, dest):
                ok = True
                break
        if ok:
            it["photos"] = [str(dest)]
            it["photo"] = str(dest)
            fetched += 1
            print(f"  OK  {name[:45]}")
        else:
            skipped += 1

    INVENTORY.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nСкачано уникальных фото: {fetched}, пропущено: {skipped}")


if __name__ == "__main__":
    main()
