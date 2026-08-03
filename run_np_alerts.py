#!/usr/bin/env python3
"""
AIOS Nova Poshta Alerts — следит за моими входящими посылками и шлёт
уведомления в Telegram:
  • 📦 новая посылка появилась в кабинете
  • 📍 посылка прибыла в отделение
  • ✅ посылка получена

Запуск по таймеру (systemd). State-файл предотвращает повторы.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

STATE = ROOT / "data" / "np_alerts_state.json"

# Статусы, при которых шлём уведомление
ARRIVAL_KEYS = ("arrived at the branch", "прибул", "прибула", "прибыл", "прибыла",
                "у відділенні", "в отделении", "на складі відділення", "у відділення")
RECEIVED_KEYS = ("received at branch", "отримана", "отримано", "получена", "получено",
                 "видано", "видана", "одержана")


def _env(key: str) -> str:
    import os
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


def _load_state() -> dict:
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def _save_state(st: dict) -> None:
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2))


def _tg(token: str, chat_id: int, text: str) -> None:
    import html as _html
    payload = {"chat_id": chat_id, "text": _html.escape(text)[:3800],
               "parse_mode": "HTML", "disable_web_page_preview": True}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60):
        pass


def _run_ac(args: list, timeout: int = 170) -> dict:
    """Вызвать run_account_control.py (my_ttns — браузер, track — API)."""
    py = "/opt/aios/.venv/bin/python"
    needs_x = not (len(args) >= 2 and args[0] == "novaposhta" and args[1] == "track")
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


def _classify(status: str) -> str:
    """'arrived' | 'received' | 'other'."""
    low = (status or "").lower()
    if any(k in low for k in RECEIVED_KEYS):
        return "received"
    if any(k in low for k in ARRIVAL_KEYS):
        return "arrived"
    return "other"


def _run_sales_lifecycle_alerts(token: str, chat_id: int) -> int:
    """Отслеживать исходящие продажи по известным ТТН.

    В отличие от старого контура входящих посылок, здесь не нужен залогиненный
    кабинет: номера уже создаются через run_ttn.py, а public tracking API
    работает быстро. Состояние/дедупликацию хранит SalesLifecycle.
    """
    try:
        from aios_core.sales_lifecycle import SalesLifecycle
        lifecycle = SalesLifecycle(ROOT)
    except Exception as exc:
        print(f"[sales] не удалось открыть lifecycle: {exc}")
        return 0

    sent = 0
    for sale in lifecycle.active_tracking_sales():
        ttn = str(sale.get("ttn") or "")
        if not ttn:
            continue
        tracked = _run_ac(["novaposhta", "track", ttn], timeout=40)
        if tracked.get("status") == "ok" and tracked.get("found"):
            result = lifecycle.apply_tracking(ttn, str(tracked.get("tracking_status") or ""))
            for text in result.get("notifications") or []:
                try:
                    _tg(token, chat_id, text)
                    sent += 1
                    print(f"  [sales] {ttn}: {text[:100]}")
                except Exception as exc:
                    print(f"  [sales] send err {ttn}: {exc}")
        elif tracked.get("status") == "error":
            print(f"  [sales] track error {ttn}: {tracked.get('error', '?')}")
        # Не спамим публичный API, если открытых сделок несколько.
        import time
        time.sleep(0.35)

    for notification in lifecycle.due_notifications():
        try:
            _tg(token, chat_id, notification["text"])
            sent += 1
            print(f"  [sales] reminder {notification['task'].get('id')}")
        except Exception as exc:
            print(f"  [sales] reminder send err: {exc}")
    return sent


def main() -> int:
    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat = _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("Нет токена/чата в .env"); return 1

    # 0) исходящие продажи: работают даже если браузерный кабинет НП разлогинен.
    lifecycle_sent = _run_sales_lifecycle_alerts(token, int(chat))

    # 1) собрать мои ТТН из кабинета (входящие)
    res = _run_ac(["novaposhta", "my_ttns"])
    if res.get("status") != "ok":
        # Не прерываем контроль исходящих: он использует публичный трекинг и
        # уже выполнился выше. Входящие уведомления просто будут повторены
        # после восстановления сессии кабинета.
        print("Не смог получить ТТН из кабинета:", res.get("error"))
        print(f"Отправлено уведомлений lifecycle: {lifecycle_sent}")
        return 0
    ttns = res.get("ttns") or []
    print(f"Найдено входящих посылок: {len(ttns)}: {ttns}")

    # 2) для каждой — трекинг (API, быстро)
    statuses = {}
    for ttn in ttns:
        t = _run_ac(["novaposhta", "track", ttn], timeout=40)
        if t.get("status") == "ok" and t.get("found"):
            statuses[ttn] = {
                "status": t.get("tracking_status") or "",
                "events": t.get("events") or [],
                "details": t.get("details") or {},
            }
            # небольшой интервал, чтобы не спамить API
            import time
            time.sleep(0.4)

    # 3) сравнить с state и отправить уведомления
    state = _load_state()
    now = datetime.now().strftime("%d.%m %H:%M")
    sent = 0

    # первый запуск — только инициализация (не спамить про уже существующие посылки)
    first_run = not state
    if first_run:
        print("Первый запуск: инициализация state без уведомлений")

    # новые посылки
    for ttn in ttns:
        if ttn not in state and not first_run:
            info = statuses.get(ttn, {})
            det = info.get("details", {})
            txt = (f"📦 <b>Новая посылка Новой Пошты</b> ({now})\n"
                   f"ТТН: <code>{ttn}</code>\n"
                   f"Маршрут: {det.get('sender') or '?'} → {det.get('recipient') or '?'}\n"
                   f"Статус: {info.get('status') or '—'}")
            try:
                _tg(token, int(chat), txt)
                sent += 1
                print(f"  → новая посылка {ttn}")
            except Exception as e:
                print(f"  ! send err: {e}")

    # прибытие / получение (смена статуса)
    for ttn, info in statuses.items():
        old = state.get(ttn, {})
        old_cls = _classify(old.get("status", ""))
        new_status = info.get("status", "")
        new_cls = _classify(new_status)
        det = info.get("details", {})
        if ttn in state and not first_run and new_cls != old_cls and new_cls in ("arrived", "received"):
            if new_cls == "arrived":
                txt = (f"📍 <b>Посылка прибыла в отделение</b> ({now})\n"
                       f"ТТН: <code>{ttn}</code>\n"
                       f"Статус: {new_status}\n"
                       f"Отделение: {det.get('recipient') or '?'}")
            else:
                txt = (f"✅ <b>Посылка получена</b> ({now})\n"
                       f"ТТН: <code>{ttn}</code>\n"
                       f"Статус: {new_status}\n"
                       f"Получатель: {det.get('recipient') or '?'}")
            try:
                _tg(token, int(chat), txt)
                sent += 1
                print(f"  → {new_cls} {ttn}")
            except Exception as e:
                print(f"  ! send err: {e}")

    # 4) сохранить state (все текущие ТТН со статусами)
    new_state = {}
    for ttn in ttns:
        new_state[ttn] = {"status": statuses.get(ttn, {}).get("status", ""),
                          "seen": now}
    # удалить ТТН, которых больше нет (посылки устарели)
    for ttn in list(state.keys()):
        if ttn not in new_state:
            pass  # оставляем в истории, чтобы не уведомлять повторно
    _save_state({**state, **new_state})

    sent += lifecycle_sent
    print(f"Отправлено уведомлений: {sent}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
