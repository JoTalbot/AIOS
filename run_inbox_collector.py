#!/usr/bin/env python3
"""Периодический сборщик инбокса + триггер harvester 50+ сообщений.

Собирает сообщения из каналов (TG, Instagram DM, Messenger, Viber, Signal,
телефон, OLX — без почты) и сохраняет кэш в data/inbox_cache.json.
После сбора асинхронно запускает run_converge_harvester.py для автоподгрузки
полных переписок (50+ сообщений) по каждому новому unread чату.
"""
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path("/root/AIOS")
sys.path.insert(0, str(ROOT))

from run_telegram_bot import _collect_inbox, _inbox_cache_save

def _trigger_harvester():
    try:
        subprocess.Popen(
            ["/opt/aios/.venv/bin/python", str(ROOT / "run_converge_harvester.py")],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass

def main() -> int:
    try:
        items, summary = _collect_inbox({})
        _inbox_cache_save(items)
        print(f"[inbox_collector] {len(items)} карточек | {summary}", flush=True)
        # если есть новые unread — сразу дергаем harvester, не ждём таймер 60с
        unread = sum(1 for it in items if isinstance(it, dict) and it.get("unread"))
        if unread:
            _trigger_harvester()
            print(f"[inbox_collector] harvester triggered for {unread} unread", flush=True)
        return 0
    except Exception as exc:
        print(f"[inbox_collector] ERROR: {exc}", flush=True)
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
