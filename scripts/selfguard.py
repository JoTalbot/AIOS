#!/usr/bin/env python3
"""
AIOS SelfGuard v1.0 — независимый сторож критичных файлов проекта.

Следит за WATCH_FILES (aios_core/self_protection.py):
- здоровый файл -> обновляет снапшот в backups/selfguard/
- повреждён/удалён (вырождение в заглушку, syntax error) -> восстанавливает из снапшота
  и шлёт алерт в Telegram.

Запуск:
  selfguard.py                  — бесконечный цикл (под systemd)
  selfguard.py --once           — разовая проверка (exit 0 если всё ок)
  selfguard.py --force-snapshot — пересоздать снапшоты из текущего состояния
                                  (после НАМЕРЕННОГО большого рефакторинга критичных файлов)
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(os.environ.get("AIOS_REPO_PATH", "/root/AIOS"))
SNAP_DIR = REPO / "backups" / "selfguard"
INTERVAL = int(os.environ.get("SELFGUARD_INTERVAL", "120"))

sys.path.insert(0, str(REPO))

# env для Telegram (токен + chat id)
for _env_path in (REPO / ".env", Path("/etc/aios/aios-auto-coder.env")):
    if _env_path.exists():
        for _line in _env_path.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _, _v = _line.partition("=")
            if _k.strip() and _k.strip() not in os.environ:
                os.environ[_k.strip()] = _v.strip().strip('"').strip("'")

from aios_core.self_protection import WATCH_FILES, check_code_health  # noqa: E402

TG_TOKEN = os.environ.get("AIOS_TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("AIOS_AUTO_CODER_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID", "")


def tg_send(text: str) -> None:
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": int(TG_CHAT_ID), "text": text[:3800], "disable_web_page_preview": True}
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except Exception as e:
        print(f"[SELFGUARD] TG send failed: {e}")


def snap_path(rel: str) -> Path:
    return SNAP_DIR / rel.replace("/", "__")


def snapshoot_all() -> None:
    """Принудительно пересоздать снапшоты из текущего состояния."""
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    for rel in WATCH_FILES:
        f = REPO / rel
        if f.exists():
            shutil.copy2(f, snap_path(rel))
            print(f"[SELFGUARD] snapshot: {rel}")
        else:
            print(f"[SELFGUARD] ПРОПУЩЕНО (нет файла): {rel}")


def check_file(rel: str) -> tuple[bool, bool, str]:
    """Возвращает (healthy, restored, reason)."""
    f = REPO / rel
    sp = snap_path(rel)
    if not f.exists():
        if sp.exists():
            shutil.copy2(sp, f)
            return False, True, "файл отсутствовал — восстановлен из снапшота"
        return False, False, "файл отсутствует, снапшота нет"

    src = f.read_text(encoding="utf-8", errors="ignore")
    old = sp.read_text(encoding="utf-8", errors="ignore") if sp.exists() else ""
    ok, reasons = check_code_health(str(f), src, old_code=old)
    if ok:
        # здоров — обновляем снапшот при изменении
        if not sp.exists() or old != src:
            SNAP_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, sp)
        return True, False, ""
    if sp.exists():
        shutil.copy2(sp, f)
        return False, True, f"{'; '.join(reasons)[:120]} — восстановлен из снапшота"
    return False, False, f"{'; '.join(reasons)[:150]} — СНАПШОТА НЕТ!"


def run_checks() -> list[str]:
    problems: list[str] = []
    for rel in WATCH_FILES:
        try:
            healthy, restored, reason = check_file(rel)
            if restored:
                problems.append(f"♻️ {rel}: {reason}")
                print(f"[SELFGUARD] RESTORED {rel}: {reason}")
            elif not healthy:
                problems.append(f"⚠️ {rel}: {reason}")
                print(f"[SELFGUARD] BROKEN {rel}: {reason}")
        except Exception as e:
            problems.append(f"⚠️ {rel}: ошибка проверки: {e}")
    return problems


def main() -> None:
    if "--force-snapshot" in sys.argv:
        snapshoot_all()
        return
    if "--once" in sys.argv:
        probs = run_checks()
        if probs:
            print("\n".join(probs))
            sys.exit(1)
        print("SELFGUARD OK — все критичные файлы здоровы, снапшоты актуальны")
        return
    print(f"[SELFGUARD] start: interval={INTERVAL}s, watch={len(WATCH_FILES)} файлов, snapshots={SNAP_DIR}")
    while True:
        probs = run_checks()
        if probs:
            tg_send("🛡️ <b>AIOS SelfGuard</b>\n" + "\n".join(probs))
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
