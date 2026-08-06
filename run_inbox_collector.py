#!/usr/bin/env python3
"""Периодический сборщик инбокса.

Собирает сообщения из каналов (TG, Instagram DM, Messenger, Viber, Signal,
телефон, OLX — без почты) и сохраняет кэш в data/inbox_cache.json.
Команда «инбокс» в боте показывает сохранённое мгновенно, не дёргая адаптеры.

Запуск по cron каждые 5 минут:
*/5 * * * * /opt/aios/.venv/bin/python /root/AIOS/run_inbox_collector.py >> /root/AIOS/logs/inbox_collector.log 2>&1
"""
import sys
import traceback
from pathlib import Path

ROOT = Path("/root/AIOS")
sys.path.insert(0, str(ROOT))

# Импортируем функции сбора из бота (main не запускается).
from run_telegram_bot import _collect_inbox, _inbox_cache_save  # noqa: E402


def main() -> int:
    try:
        items, summary = _collect_inbox({})
        _inbox_cache_save(items)
        print(f"[inbox_collector] {len(items)} карточек | {summary}", flush=True)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[inbox_collector] ERROR: {exc}", flush=True)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
