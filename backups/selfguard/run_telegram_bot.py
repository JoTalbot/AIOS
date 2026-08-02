"""
AIOS Telegram Bot — управление агентами через Telegram.

Запуск::
    export AIOS_TELEGRAM_TOKEN="123456:ABC-DEF..."
    python run_telegram_bot.py

Команды:
    /start      — приветствие
    /stats      — статистика системы (БД, оркестратор, бэкапы)
    /status     — сводка по платформам
    /olx        — статистика OLX (объявления, цены)
    /olx_sub    — подписка на новые объявления по запросу
    /olx_unsub  — отписка
    /olx_list   — список моих подписок
    /olx_latest— последние объявления по подписке
    /olx_analytics — AI-аналитика цен по запросу
    /help       — список команд

Архитектура:
    - Polling-режим (не нужен публичный URL)
    - Интегрируется с ``aios_core.container``
    - Без внешних зависимостей — чистые HTTP-запросы к Telegram API
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _, _value = _line.partition("=")
        _key = _key.strip()
        _value = _value.strip().strip('\"').strip("'")
        if _key and _key not in os.environ:
            os.environ[_key] = _value

# ---------------------------------------------------------------------------
# Telegram API helpers (zero-dependency)
# ---------------------------------------------------------------------------


class TelegramAPI:
    """Minimal Telegram Bot API client (polling mode)."""

    def __init__(self, token: str) -> None:
        self._token = token
        self._base = f"https://api.telegram.org/bot{token}"

    def _request(self, method: str, data: dict | None = None) -> dict:
        url = f"{self._base}/{method}"
        body = json.dumps(data or {}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read())

    def get_updates(self, offset: int = 0) -> list[dict]:
        result = self._request("getUpdates", {"offset": offset, "timeout": 30})
        return result.get("result", [])

    def send_message(
        self, chat_id: int, text: str, parse_mode: str = "HTML", disable_web_page_preview: bool = True,
        reply_markup: dict | None = None,
    ) -> dict:
        payload = {
            "chat_id": chat_id,
            "text": text[:4000],
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self._request("sendMessage", payload)

    def answer_callback(self, callback_query_id: str, text: str = "") -> dict:
        return self._request("answerCallbackQuery", {
            "callback_query_id": callback_query_id,
            "text": text[:200],
        })

    def edit_message(self, chat_id: int, message_id: int, text: str,
                     parse_mode: str = "HTML", reply_markup: dict | None = None) -> dict:
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text[:4000],
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self._request("editMessageText", payload)

    def get_file(self, file_id: str) -> dict:
        """Получить информацию о файле (file_path) по file_id."""
        return self._request("getFile", {"file_id": file_id}).get("result", {})

    def download_file_by_id(self, file_id: str, dest: str | None = None) -> str:
        """Скачать файл (фото и т.п.) по file_id в локальный путь; вернуть путь."""
        info = self.get_file(file_id)
        path = info.get("file_path", "")
        if not path:
            raise ValueError(f"Нет file_path для file_id {file_id}")
        url = f"https://api.telegram.org/file/bot{self._token}/{path}"
        with urllib.request.urlopen(url, timeout=90) as resp:
            data = resp.read()
        if not dest:
            ext = Path(path).suffix or ".jpg"
            dest = f"/tmp/aios_tg_{int(time.time() * 1000)}{ext}"
        Path(dest).write_bytes(data)
        return dest

    def _multipart(self, method: str, chat_id: int, field: str, file_path: str,
                   caption: str = "") -> dict:
        """Универсальная отправка файла (photo/document)."""
        import mimetypes
        boundary = "----aios" + str(int(time.time() * 1000))
        content = Path(file_path).read_bytes()

        def _field(name: str, value: str) -> bytes:
            return (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                    f"{value}\r\n").encode()

        fn = Path(file_path).name
        ct = mimetypes.guess_type(fn)[0] or "application/octet-stream"
        body = b"".join([
            _field("chat_id", str(chat_id)),
            _field("caption", caption[:1000]) if caption else b"",
            (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; filename=\"{fn}\"\r\n"
             f"Content-Type: {ct}\r\n\r\n").encode(),
            content,
            f"\r\n--{boundary}--\r\n".encode(),
        ])
        req = urllib.request.Request(
            f"{self._base}/{method}", data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read())

    def send_photo(self, chat_id: int, photo_path: str, caption: str = "") -> dict:
        return self._multipart("sendPhoto", chat_id, "photo", photo_path, caption)

    def send_document(self, chat_id: int, file_path: str, caption: str = "") -> dict:
        return self._multipart("sendDocument", chat_id, "document", file_path, caption)


# ---------------------------------------------------------------------------
# Command handlers — каждая возвращает строку для отправки в чат
# ---------------------------------------------------------------------------


def _safe(fn):
    """Wrapper — catch all exceptions, return error string."""

    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as exc:
            import traceback

            traceback.print_exc()
            return f"❌ Ошибка: {exc}"

    return wrapper


@_safe
def _local_api_json(path: str) -> dict:
    """Read a trusted local AIOS API endpoint for Telegram status commands."""
    with urllib.request.urlopen(f"http://127.0.0.1:8000{path}", timeout=10) as response:
        return json.loads(response.read())


@_safe
def cmd_system_health() -> str:
    data = _local_api_json("/api/system-health")
    lines = ["❤️ <b>System Health</b>", ""]
    lines.append(f"CPU: {data.get('cpu_percent')}%")
    lines.append(f"RAM: {data.get('memory_percent')}%")
    lines.append(f"Disk: {data.get('disk_percent')}%")
    for service in data.get("services", []):
        mark = "✅" if service.get("status") == "ok" else "❌"
        lines.append(f"{mark} {service.get('name')}: {service.get('status')}")
    return "\n".join(lines)


@_safe
def cmd_last_backup() -> str:
    data = _local_api_json("/api/backups")
    backups = data.get("backups", [])
    if not backups:
        return "💾 <b>Backup</b>\n\nЛокальных копий пока нет."
    item = backups[0]
    return "💾 <b>Last Backup</b>\n\n" + f"ID: <code>{item.get('backup_id', item.get('id'))}</code>\n" + f"Created: {item.get('created_at', '—')}\n" + f"Verified: {'✅' if item.get('verified') else '❌'}"


@_safe
def cmd_alert_history() -> str:
    path = Path("/var/lib/aios-health-alert/state.json")
    if not path.exists():
        return "🚨 <b>Alert History</b>\n\nНет сохранённых health-check данных."
    state = json.loads(path.read_text())
    failed = [name for name, value in state.items() if not value]
    return "🚨 <b>Alert History</b>\n\n" + ("✅ Текущие проверки в норме" if not failed else "❌ Проблемы: " + ", ".join(failed))


def cmd_start() -> str:
    return "🤖 <b>AIOS Control Panel</b>\n\nВыберите раздел:"

MAIN_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "🧠 Кодер"}, {"text": "📊 Статистика"}],
        [{"text": "🛒 OLX"}, {"text": "📱 Платформы"}],
        [{"text": "🌐 Аккаунты"}, {"text": "🖥 Сервер"}],
        [{"text": "🐳 Docker"}, {"text": "❤️ Health"}],
        [{"text": "💾 Backup"}, {"text": "🚨 Alerts"}],
        [{"text": "🔑 API Ключи"}, {"text": "📋 Логи"}],
        [{"text": "🤖 Бот"}, {"text": "❓ Помощь"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}

CODER_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "📋 Статус"}, {"text": "📦 Бэклог"}],
        [{"text": "⚖️ Балансер"}, {"text": "📜 Git"}],
        [{"text": "🔍 Review Bot"}, {"text": "🔍 Review Coder"}],
        [{"text": "✨ Написать код"}, {"text": "🔧 Исправить"}],
        [{"text": "🚀 Push"}, {"text": "🔄 Перезапуск"}],
        [{"text": "◀️ Меню"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}

OLX_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "📊 OLX Стат"}, {"text": "📋 Подписки"}],
        [{"text": "🆕 Последние"}, {"text": "📈 Аналитика"}],
        [{"text": "◀️ Меню"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}

ACCOUNTS_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "🌐 Google"}, {"text": "📸 Instagram"}],
        [{"text": "📘 Facebook"}, {"text": "🎵 TikTok"}],
        [{"text": "🛒 OLX"}, {"text": "◀️ Меню"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}

GOOGLE_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "✉️ Непрочитанные"}, {"text": "📥 Последние письма"}],
        [{"text": "🔍 Поиск письма"}, {"text": "📧 Отправить письмо"}],
        [{"text": "👤 Кто я"}, {"text": "📅 События"}],
        [{"text": "➕ Событие"}, {"text": "📄 Документ"}],
        [{"text": "🗂 Диск"}, {"text": "📷 Скрин почты"}],
        [{"text": "◀️ Аккаунты"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}

INSTAGRAM_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "👤 Мой профиль"}, {"text": "📈 Подписчики"}],
        [{"text": "🖼 Мои посты"}, {"text": "📷 Скрин профиля"}],
        [{"text": "💬 Директ"}, {"text": "❤️ Лайкнуть"}],
        [{"text": "👤 Подписка"}, {"text": "◀️ Аккаунты"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}



@_safe
def cmd_stats() -> str:
    from aios_core.container import container

    db = container.db()
    orch = container.orchestrator()
    bm = container.backup_manager()
    db_stats = db.stats()
    orch_stats = orch.stats()
    bu_health = bm.health_report()

    tables_info = "\n".join(f"    <code>{t}</code>: {c} строк" for t, c in sorted(db_stats.get("tables", {}).items()))
    return (
        f"📊 <b>Статистика AIOS</b>\n\n"
        f"🗄️ <b>База данных</b>\n"
        f"  Путь: <code>{db_stats['db_path']}</code>\n"
        f"  Диалект: <code>{db_stats['dialect']}</code>\n"
        f"  Таблицы:\n{tables_info}\n\n"
        f"⚙️ <b>Оркестратор</b>\n"
        f"  Задач: {orch_stats.get('tasks', '?')}\n\n"
        f"💾 <b>Бэкапы</b>\n"
        f"  Всего: {bu_health['total_backups']}\n"
        f"  Размер: {bu_health['total_size_mb']} MB\n"
        f"  Директория: <code>{bu_health['backup_dir']}</code>"
    )


@_safe
def cmd_platforms() -> str:
    from aios_core.platforms import list_platforms

    plats = list_platforms()
    lines = [f"📱 <b>Платформы</b> ({len(plats)})\n"]
    lines.extend(f"  • <code>{p.name}</code> — <code>{p.android_package}</code>" for p in plats)
    return "\n".join(lines)


def _get_ads_db():
    import sqlite3

    db_path = os.environ.get("AIOS_OLX_HTTP_DB", "/root/AIOS/data/olx_http.sqlite")
    if not Path(db_path).exists():
        return None, f"⚠️ База OLX не найдена по пути {db_path}"
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn, None


@_safe
def cmd_olx(args: str = "") -> str:
    conn, err = _get_ads_db()
    if err:
        return err
    try:
        total = conn.execute("SELECT COUNT(*) FROM ads").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM ads WHERE active=1").fetchone()[0]
        if total == 0:
            return "📭 База OLX пуста."
        queries = conn.execute(
            "SELECT query, COUNT(*) as cnt FROM ads WHERE active=1 GROUP BY query ORDER BY cnt DESC LIMIT 10"
        ).fetchall()
        price_row = conn.execute(
            "SELECT MIN(price_value), MAX(price_value), AVG(price_value) FROM ads "
            "WHERE price_value > 0 AND price_currency='UAH'"
        ).fetchone()
        last_run = conn.execute("SELECT ts, parsed FROM collection_runs ORDER BY ts DESC LIMIT 1").fetchone()
        qlines = "\n".join(f"  • <code>{q['query']}</code>: {q['cnt']}" for q in queries)
        return (
            f"🛒 <b>OLX Статистика</b>\n\n"
            f"  Всего собрано: <b>{total:,}</b>\n"
            f"  Активных: <b>{active:,}</b>\n"
            f"  Цены (грн): мин <b>{int(price_row[0]):,}</b> · макс <b>{int(price_row[1]):,}</b> · "
            f"сред <b>{price_row[2]:,.0f}</b>\n"
            f"  Последний цикл: {last_run['ts'][:19] if last_run else '—'} "
            f"({last_run['parsed'] if last_run else 0} объявлений)\n\n"
            f"📋 <b>По запросам:</b>\n{qlines}"
        )
    finally:
        conn.close()


@_safe
def cmd_olx_sub(args: str, chat_id: int, username: str | None, first_name: str | None) -> str:
    import olx_alerts

    parts = args.strip().split()
    if not parts:
        return "ℹ️ Использование: <code>/olx_sub iPhone 5000 20000</code>\n(запрос [мин_цена макс_цена])"
    # Parse optional min/max price at end (numeric)
    min_p = max_p = None
    if len(parts) >= 3:
        try:
            min_p = float(parts[-2].replace(",", "."))
            max_p = float(parts[-1].replace(",", "."))
            parts = parts[:-2]
        except ValueError:
            pass
    if len(parts) >= 2:
        with contextlib.suppress(ValueError):
            float(parts[-1].replace(",", "."))
    query = " ".join(parts)
    if not query:
        return "❌ Укажите поисковый запрос."
    subs = olx_alerts.init_subs_db()
    olx_alerts.subscribe_chat(
        subs, chat_id, query, username=username, first_name=first_name, min_price=min_p, max_price=max_p
    )
    filter_txt = ""
    if min_p or max_p:
        filter_txt = f"\n💵 Фильтр: {int(min_p) if min_p else 0} – {int(max_p) if max_p else '∞'} грн"
    return f"✅ Подписка оформлена на «<b>{query}</b>».{filter_txt}\n🔔 Новые объявления будут приходить автоматически."


@_safe
def cmd_olx_unsub(args: str, chat_id: int) -> str:
    import olx_alerts

    query = args.strip() or None
    subs = olx_alerts.init_subs_db()
    olx_alerts.unsubscribe_chat(subs, chat_id, query)
    if query:
        return f"🗑️ Подписка на «<b>{query}</b>» удалена."
    return "🗑️ Все подписки удалены."


@_safe
def cmd_olx_list(chat_id: int) -> str:
    import olx_alerts

    subs = olx_alerts.init_subs_db()
    items = olx_alerts.list_subscriptions(subs, chat_id)
    if not items:
        return "📭 У вас нет активных подписок.\nОформите: <code>/olx_sub &lt;запрос&gt;</code>"
    lines = ["📋 <b>Ваши подписки:</b>\n"]
    for it in items:
        f = ""
        if it["min_price"] or it["max_price"]:
            f = f" · 💵 {int(it['min_price'] or 0)}-{int(it['max_price']) if it['max_price'] else '∞'} грн"
        lines.append(f"  • <code>{it['query']}</code>{f}")
    return "\n".join(lines)


@_safe
def cmd_olx_latest(args: str, chat_id: int) -> str:
    parts = args.strip().split()
    n = 5
    if parts and parts[-1].isdigit():
        n = min(int(parts[-1]), 15)
        parts = parts[:-1]
    query = " ".join(parts)
    conn, err = _get_ads_db()
    if err:
        return err
    try:
        if query:
            rows = conn.execute(
                "SELECT * FROM ads WHERE query=? AND active=1 ORDER BY collected_at DESC LIMIT ?", (query, n)
            ).fetchall()
        else:
            # Use first subscribed query
            import olx_alerts

            subs = olx_alerts.init_subs_db()
            items = olx_alerts.list_subscriptions(subs, chat_id)
            if not items:
                return "ℹ️ Укажите запрос: <code>/olx_latest iPhone</code> или подпишитесь через /olx_sub"
            query = items[0]["query"]
            rows = conn.execute(
                "SELECT * FROM ads WHERE query=? AND active=1 ORDER BY collected_at DESC LIMIT ?", (query, n)
            ).fetchall()
        if not rows:
            return f"📭 Нет объявлений по запросу «{query}»"
        import olx_alerts

        stats = olx_alerts.compute_price_stats(conn, query)
        out = [f"🛒 <b>Последние объявления</b> «{query}»:\n"]
        for r in rows:
            ad = dict(r)
            price = ad.get("price_value")
            cur = ad.get("price_currency") or "грн"
            if price is None:
                price_str = "💵 Договірна"
            else:
                tag = ""
                if stats and cur == "UAH":
                    tag = " " + olx_alerts.price_assessment(stats, price).split()[0]
                price_str = f"💵 {int(price):,} {cur}{tag}".replace(",", " ")
            title = (ad.get("title") or "(без назви)")[:80]
            url = ad.get("url") or "#"
            city = ad.get("city") or "?"
            out.append(f'• <a href="{url}">{title}</a>\n  {price_str} · 📍{city}')
        return "\n".join(out)
    finally:
        conn.close()


@_safe
def cmd_olx_analytics(args: str) -> str:
    parts = args.strip().split()
    if parts and parts[-1].isdigit():
        parts = parts[:-1]
    query = " ".join(parts)
    if not query:
        return "ℹ️ Использование: <code>/olx_analytics iPhone</code>"
    conn, err = _get_ads_db()
    if err:
        return err
    try:
        import olx_alerts

        stats = olx_alerts.compute_price_stats(conn, query)
        if not stats:
            return f"📭 Нет данных по запросу «{query}». Попробуйте сначала собрать."
        # Top 5 cheapest
        cheapest = conn.execute(
            "SELECT title, price_value, url, city FROM ads "
            "WHERE query=? AND active=1 AND price_currency='UAH' AND price_value>0 "
            "ORDER BY price_value ASC LIMIT 5",
            (query,),
        ).fetchall()
        out = [
            f"📊 <b>AI-аналитика цен</b> «{query}»:\n",
            f"  📦 Объявлений в выборке: <b>{stats.count}</b>",
            f"  💸 Мин: <b>{int(stats.min_p):,} грн</b>",
            f"  📈 Макс: <b>{int(stats.max_p):,} грн</b>",
            f"  ⚖️ Медиана: <b>{int(stats.median):,} грн</b>",
            f"  📉 P10 (очень дёшево): <b>{int(stats.p10):,} грн</b>",
            f"  📈 P90 (очень дорого): <b>{int(stats.p90):,} грн</b>",
            f"  🧮 Средняя: <b>{stats.avg:,.0f} грн</b>\n",
            "🔥 <b>ТОП-5 самых дешёвых:</b>",
        ]
        for r in cheapest:
            title = (r["title"] or "")[:55]
            out.append(f'  • <a href="{r["url"]}">{title}</a> — {int(r["price_value"]):,} грн ({r["city"]})')
        return "\n".join(out).replace(",", " ")
    finally:
        conn.close()


@_safe
def cmd_help() -> str:
    return (
        "🤖 <b>AIOS Telegram Bot — Команды</b>\n\n"
        "  /start — приветствие\n"
        "  /stats — статистика БД и оркестратора\n"
        "  /status — зарегистрированные платформы\n"
        "  /olx — общая статистика OLX\n"
        "  /olx_sub &lt;запрос&gt; [min max] — подписка на новые объявления\n"
        "  /olx_unsub [запрос] — отписка (без аргументов = все)\n"
        "  /olx_list — мои подписки\n"
        "  /olx_latest &lt;запрос&gt; [N] — последние N объявлений\n"
        "  /olx_analytics &lt;запрос&gt; — AI-аналитика цен\n"
        "  /accounts — управление Google и Instagram аккаунтами\n"
        "  /google — быстрые команды Google (почта, календарь, диск)\n"
        "  /instagram — быстрые команды Instagram (профиль, посты)\n\n"
        "<i>Просто напишите боту обычным текстом, например:</i>\n"
        "  «проверь мою почту» · «сколько непрочитанных» · «кто я в гугле»\n"
        "  «покажи календарь» · «покажи мой инстаграм» · «мои посты» · «отправь письмо ...»\n\n"
        "<i>Бот работает в polling-режиме. Алерты приходят автоматически после каждого цикла сбора (каждые 30 мин).</i>"
    )




# ---------------------------------------------------------------------------
# Account control — Google + Instagram через обычный диалог
# ---------------------------------------------------------------------------

# Последнее фото, присланное пользователем (для будущих действий): chat_id -> путь
_last_photo: dict[int, str] = {}
# Последнее видео, присланное пользователем (для TikTok upload): chat_id -> путь
_last_video: dict[int, str] = {}
# Последние id писем, показанных в чате: chat_id -> [ids...]
_last_gmail_ids: dict[int, list[str]] = {}
# Ожидающие подтверждения действий: chat_id -> {"kind": ..., "data": ...}
_pending_confirm: dict[int, dict] = {}


def _run_account_control(args: list[str], timeout: int = 160) -> dict:
    """Запустить run_account_control.py (хелпер управления аккаунтами)."""
    import subprocess as _sp
    py = "/opt/aios/.venv/bin/python"
    helper = str(PROJECT_ROOT / "run_account_control.py")
    # IMAP/SMTP-команды не требуют X; браузерные — требуют xvfb
    # viber — нативный десктоп на постоянном дисплее :1 (без xvfb)
    if args and args[0] == "viber":
        needs_x = False
    else:
        needs_x = not (len(args) >= 2 and args[0] == "google" and args[1] in ("gmail_list", "gmail_send", "gmail_search", "open"))
    if needs_x:
        cmd = ["xvfb-run", "-a", "-s", "-screen 0 1440x900x24", py, helper] + args
    else:
        cmd = [py, helper] + args
    try:
        r = _sp.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(PROJECT_ROOT))
    except _sp.TimeoutExpired:
        return {"status": "error", "error": "Превышено время выполнения (браузер может быть занят)"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}
    out_txt = (r.stdout or "").strip()
    if not out_txt:
        return {"status": "error", "error": (r.stderr or "пустой ответ")[-400:]}
    try:
        # JSON может быть последней строкой или всем выводом
        start = out_txt.find("{")
        return json.loads(out_txt[start:]) if start >= 0 else {"status": "error", "error": out_txt[-400:]}
    except Exception:
        return {"status": "error", "error": out_txt[-400:]}


def _fmt_gmail_list(data: dict, unread_only: bool = False) -> str:
    emails = data.get("emails", [])
    if not emails:
        return "📭 Писем не найдено."
    head = f"📥 <b>{'Непрочитанные' if unread_only else 'Последние'} письма</b>\n"
    head += f"Всего: {data.get('total', '?')} · 🔴 непрочитанных: {data.get('unread_total', '?')}\n\n"
    lines = [head]
    for i, e in enumerate(emails, 1):
        if "error" in e:
            lines.append(f"{i}. ❌ {e['error']}")
            continue
        mark = "🔴 " if e.get("unread") else ""
        subj = e.get("subject", "(без темы)")
        frm = e.get("from", "?")
        date = (e.get("date") or "")[:22]
        snip = (e.get("snippet") or "")[:180]
        lines.append(f"{i}. {mark}<b>{subj}</b>\n   ✉️ {frm}\n   🕐 {date}\n   {snip}")
    return "\n\n".join(lines)


def _acct_send_result(api, chat_id: int, data: dict, intro: str) -> None:
    if data.get("status") == "error":
        api.send_message(chat_id, f"❌ {data.get('error', 'неизвестная ошибка')}")
        return
    api.send_message(chat_id, intro + (data.get("text", "")), parse_mode="HTML")
    shot = data.get("screenshot")
    if shot and os.path.exists(shot):
        try:
            api.send_photo(chat_id, shot, caption=data.get("caption", ""))
        except Exception as e:
            print(f"  [ACCT] send_photo failed: {e}")


def _run_acct_cmd(api, chat_id: int, args: list, kind: str) -> None:
    """Универсальный запуск команд аккаунтов (facebook/tiktok/olx)."""
    data = _run_account_control(args)
    if data.get("status") != "ok":
        api.send_message(chat_id, f"❌ {data.get('error', 'ошибка')}")
        return
    if kind == "facebook":
        f = data.get("facebook", {})
        txt = (f"📘 <b>Facebook</b>\n👤 Имя: {_esc_tg(f.get('name'))}\n"
               f"👥 Друзья: {f.get('friends') or '?'}\n"
               f"📍 {_esc_tg(f.get('city') or '—')}\n"
               f"ℹ️ {_esc_tg(f.get('bio') or 'без описания')}\n"
               f"🔗 {f.get('profile_url')}\n🔔 Уведомлений: {f.get('notifications') or 0}")
    elif kind == "tiktok":
        p = data.get("tiktok", {})
        txt = (f"🎵 <b>TikTok</b>\n👤 Имя: {_esc_tg(p.get('name') or p.get('username'))}\n"
               f"👥 Подписчики: {p.get('followers') or 0} · 🔄 Подписки: {p.get('following') or 0}\n"
               f"❤️ Лайки: {p.get('likes') or 0}\nℹ️ {_esc_tg(p.get('bio') or '—')}\n"
               f"🔗 {p.get('profile_url')}")
    elif kind == "olx":
        o = data.get("olx", {})
        txt = (f"🛒 <b>OLX</b>\n👤 Имя: {_esc_tg(o.get('name') or '?')}\n"
               f"📄 Объявлений: {o.get('ads_count') or 0}\n"
               f"💰 Баланс: {o.get('balance') or 0} грн\n🔑 Логин: {o.get('login')}")
    else:
        txt = str(data)[:300]
    _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                     "screenshot": data.get("screenshot") or
                                     (data.get("facebook") or data.get("tiktok") or data.get("olx") or {}).get("screenshot"),
                                     "caption": {"facebook": "📘 Facebook", "tiktok": "🎵 TikTok",
                                                 "olx": "🛒 OLX"}.get(kind, "")}, "")


def _acct_google(api, chat_id: int, kind: str, extra: str = "") -> None:
    api.send_message(chat_id, "⏳ Секунду, работаю с Google…")
    if kind == "whoami":
        data = _run_account_control(["google", "whoami"])
        if data.get("status") == "ok":
            email = data.get("email") or "?"
            raw = (data.get("raw") or email).replace("\n", " ")
            api.send_message(chat_id,
                             f"👤 <b>Google аккаунт в Chrome:</b>\n{raw}\n\n"
                             f"Почта (IMAP): <code>{email}</code>")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', 'ошибка')}")
    elif kind == "unread":
        data = _run_account_control(["google", "gmail_list", "5", "--unread"])
        if data.get("status") == "ok":
            _last_gmail_ids[chat_id] = [e.get("id", "") for e in data.get("emails", [])]
        _acct_send_result(api, chat_id, {"status": data.get("status"),
                                         "error": data.get("error"),
                                         "text": _fmt_gmail_list(data, unread_only=True)}, "")
    elif kind == "list":
        data = _run_account_control(["google", "gmail_list", "5"])
        if data.get("status") == "ok":
            _last_gmail_ids[chat_id] = [e.get("id", "") for e in data.get("emails", [])]
        _acct_send_result(api, chat_id, {"status": data.get("status"),
                                         "error": data.get("error"),
                                         "text": _fmt_gmail_list(data)}, "")
    elif kind == "calendar":
        data = _run_account_control(["google", "screenshot", "calendar"])
        _acct_send_result(api, chat_id,
                          {"status": data.get("status"), "error": data.get("error"),
                           "text": f"📅 <b>Google Календарь</b>\n{data.get('title', '')}\n{data.get('url', '')}",
                           "screenshot": data.get("screenshot"),
                           "caption": "📅 Календарь (скриншот)"}, "")
    elif kind == "drive":
        data = _run_account_control(["google", "screenshot", "drive"])
        _acct_send_result(api, chat_id,
                          {"status": data.get("status"), "error": data.get("error"),
                           "text": f"🗂 <b>Google Диск</b>\n{data.get('title', '')}\n{data.get('url', '')}",
                           "screenshot": data.get("screenshot"),
                           "caption": "🗂 Диск (скриншот)"}, "")
    elif kind == "mailshot":
        data = _run_account_control(["google", "screenshot", "gmail"])
        _acct_send_result(api, chat_id,
                          {"status": data.get("status"), "error": data.get("error"),
                           "text": f"📧 <b>Почта Gmail</b>\n{data.get('title', '')}\n{data.get('url', '')}",
                           "screenshot": data.get("screenshot"),
                           "caption": "📧 Gmail (скриншот)"}, "")
    elif kind == "events":
        data = _run_account_control(["google", "calendar_events"])
        if data.get("status") == "ok":
            evs = data.get("events") or []
            if evs:
                text = "📅 <b>События на сегодня:</b>\n" + "\n".join(f"• {e}" for e in evs)
            else:
                text = "📅 Событий на сегодня нет."
            _acct_send_result(api, chat_id, {"status": "ok", "text": text,
                                             "screenshot": data.get("screenshot"),
                                             "caption": "📅 Календарь (сегодня)"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', 'ошибка')}")
    elif kind == "send_prompt":
        api.send_message(chat_id,
                         "📧 <b>Отправка письма</b>\n\n"
                         "Напишите одним сообщением: <i>кому, тема, текст</i>.\n"
                         "Например: «отправь письмо ivan@gmail.com, тема Встреча, "
                         "текст: привет, созвонимся завтра в 15:00»")
    elif kind == "event_prompt":
        api.send_message(chat_id,
                         "📅 <b>Создание события</b>\n\n"
                         "Напишите, например: «событие Встреча с Мишей завтра в 14:00»,\n"
                         "или «добавь событие Отчёт 05.08 в 10:30»")
    elif kind == "search_prompt":
        api.send_message(chat_id,
                         "🔍 <b>Поиск в почте</b>\n\n"
                         "Напишите «найди письмо <запрос>», например «найди письмо от github»")
    elif kind == "docs_prompt":
        api.send_message(chat_id,
                         "📄 <b>Создание документа</b>\n\n"
                         "Напишите «создай документ, тема <название>, текст: <содержимое>»")
    else:
        api.send_message(chat_id, "❌ Неизвестная команда Google.")


def _acct_instagram(api, chat_id: int, kind: str, extra: str = "") -> None:
    api.send_message(chat_id, "⏳ Секунду, захожу в Instagram…")
    if kind in ("profile", "stats"):
        data = _run_account_control(["instagram", "profile"])
        if data.get("status") == "ok":
            p = data.get("profile", {})
            text = (f"📸 <b>Instagram: @{p.get('username', '?')}</b>\n"
                    f"👤 Имя: {p.get('full_name') or '—'}\n"
                    f"👥 Подписчики: {p.get('followers') or 0}\n"
                    f"🔄 Подписки: {p.get('following') or 0}\n"
                    f"📄 Постов: {p.get('posts_count') or 0}\n"
                    f"ℹ️ {p.get('bio') or 'без описания'}\n"
                    f"🔗 {p.get('profile_url') or ''}")
            _acct_send_result(api, chat_id,
                              {"status": "ok", "text": text,
                               "screenshot": data.get("screenshot"),
                               "caption": f"📸 @{p.get('username')}"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', 'ошибка')}")
    elif kind == "posts":
        data = _run_account_control(["instagram", "posts", "5"])
        if data.get("status") == "ok":
            posts = data.get("posts") or []
            if not posts:
                api.send_message(chat_id,
                                 f"🖼 <b>@{(data.get('username') or '?')}</b>: постов пока нет.")
                return
            lines = [f"🖼 <b>Последние посты @{data.get('username')}</b>:"]
            for i, p in enumerate(posts, 1):
                alt = (p.get("alt") or "")[:80]
                lines.append(f"{i}. <a href=\"{p.get('url')}\">/p/{p.get('code')}</a>  {alt}")
            api.send_message(chat_id, "\n".join(lines))
        else:
            api.send_message(chat_id, f"❌ {data.get('error', 'ошибка')}")
    elif kind == "screenshot":
        data = _run_account_control(["instagram", "screenshot"])
        _acct_send_result(api, chat_id,
                          {"status": data.get("status"), "error": data.get("error"),
                           "text": f"📸 <b>Instagram</b>: @{data.get('username', '?')}",
                           "screenshot": data.get("screenshot"),
                           "caption": "📸 Профиль Instagram"}, "")
    elif kind == "like_prompt":
        api.send_message(chat_id,
                         "❤️ <b>Лайк</b>: пришлите ссылку на пост, например:\n"
                         "«лайкни https://www.instagram.com/p/CODE/»")
    elif kind == "follow_prompt":
        api.send_message(chat_id,
                         "👤 <b>Подписка</b>: напишите\n"
                         "«подпишись на @username» или «отпишись от @username»")
    elif kind == "dm_prompt":
        api.send_message(chat_id,
                         "💬 <b>Директ Instagram</b>\n\n"
                         "• «директ» — список чатов\n"
                         "• «покажи чат Серега» — последние сообщения\n"
                         "• «напиши в директ Серега: привет» — отправить (с подтверждением)\n"
                         "• «напиши в директ @username: текст» — новый чат")
    else:
        api.send_message(chat_id, "❌ Неизвестная команда Instagram.")


def _llm_extract_json(prompt: str) -> dict:
    """Универсальный LLM-вызов: вернуть JSON из промпта."""
    import urllib.request as _urllib
    _b = None
    try:
        from aios_core.llm_balancer import LLMBalancer as _LB
        _b = _LB()
    except Exception:
        _b = None
    response = None
    if _b is not None:
        try:
            response = _b.chat([{"role": "user", "content": prompt}],
                               model=os.environ.get("LLM_MODEL", "meta-llama/llama-4-maverick"),
                               system="You extract JSON only.", max_tokens=400, temperature=0.0,
                               task_type="chat")
        except Exception:
            response = None
    if not response:
        try:
            key = os.environ.get("OPENROUTER_API_KEY", "")
            if key:
                payload = json.dumps({
                    "model": "mistralai/mistral-small-3.2-24b-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 400, "temperature": 0.0,
                }).encode()
                req = _urllib.Request("https://openrouter.ai/api/v1/chat/completions",
                                      data=payload, headers={
                                          "Content-Type": "application/json",
                                          "Authorization": "Bearer " + key})
                with _urllib.urlopen(req, timeout=45) as resp:
                    data = json.loads(resp.read())
                response = data["choices"][0]["message"]["content"]
        except Exception:
            pass
    if not response:
        return {}
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except Exception:
        pass
    return {}


def _llm_extract_gmail(text: str) -> dict:
    """LLM: извлечь {to, subject, body} из запроса на отправку письма."""
    prompt = (
        "Ты — парсер. Извлеки из сообщения данные для письма. "
        "Верни ТОЛЬКО JSON без пояснений: {\"to\": \"email\", \"subject\": \"тема\", \"body\": \"текст\"}. "
        "Если адреса нет — to=''. Если темы нет — subject=''. "
        f"Сообщение: {text}"
    )
    return _llm_extract_json(prompt)


def _llm_extract_calendar(text: str) -> dict:
    """LLM: извлечь {title, date, time, desc} из запроса на создание события."""
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    prompt = (
        "Ты — парсер событий календаря. Извлеки из сообщения данные события. "
        "Верни ТОЛЬКО JSON без пояснений: "
        "{\"title\": \"название\", \"date\": \"YYYY-MM-DD\", \"time\": \"HH:MM\", \"desc\": \"описание\"}. "
        f"Сегодня = {today}, завтра = {tomorrow}. Если дата не указана — date='' (значит сегодня). "
        "Если время не указано — time='' (значит 12:00). Если описания нет — desc=''. "
        f"Сообщение: {text}"
    )
    return _llm_extract_json(prompt)


def _esc_tg(s) -> str:
    import html
    return html.escape(str(s or ""))


# --------------------------------------------------------------- Напоминания
REMINDERS_FILE = PROJECT_ROOT / "data" / "reminders.json"


def _load_reminders() -> list[dict]:
    try:
        return json.loads(REMINDERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_reminders(items: list[dict]) -> None:
    REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    REMINDERS_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _handle_reminder(api, chat_id: int, text: str) -> None:
    """«напомни [завтра/сегодня/в] <HH:MM> <текст>»."""
    import re as _re
    text_clean = _re.sub(r"^(напомни|напоминание|remind)\s*:?\s*", "", text, flags=_re.IGNORECASE).strip()
    # время HH:MM
    m_time = _re.search(r"\b(\d{1,2})[:.](\d{2})\b", text_clean)
    # день
    day_off = 0
    if any(w in text_clean.lower() for w in ("завтра", "tomorrow")):
        day_off = 1
    elif any(w in text_clean.lower() for w in ("послезавтра", "day after")):
        day_off = 2
    elif any(w in text_clean.lower() for w in ("сегодня", "today")):
        day_off = 0
    elif "через" in text_clean.lower():
        m_h = _re.search(r"через\s+(\d+)\s*(час|ч|мин|минут)", text_clean.lower())
        if m_h:
            n = int(m_h.group(1))
            unit = m_h.group(2)
            now = datetime.now()
            if unit.startswith("ч"):
                target = now + timedelta(hours=n)
            else:
                target = now + timedelta(minutes=n)
            body = _re.sub(r"через\s+\d+\s*(час|ч|мин|минут)\s*", "", text_clean, flags=_re.IGNORECASE).strip()
            reminders = _load_reminders()
            reminders.append({"chat_id": chat_id, "at": target.isoformat(), "text": body})
            _save_reminders(reminders)
            api.send_message(chat_id, f"⏰ Напомню через {n} {unit} (в {target.strftime('%H:%M')}): «{body[:100]}»")
            return

    if not m_time:
        api.send_message(chat_id, "⏰ Формат: «напомни завтра в 15:00 позвонить Мише»\n"
                                  "или «напомни через 30 минут выпить воды»")
        return
    hh, mm = int(m_time.group(1)), int(m_time.group(2))
    body = _re.sub(r"\b\d{1,2}[:.]\d{2}\b", "", text_clean).strip()
    body = _re.sub(r"^(завтра|сегодня|послезавтра|tomorrow|today)\s*", "", body, flags=_re.IGNORECASE).strip()
    target = datetime.now() + timedelta(days=day_off)
    target = target.replace(hour=hh, minute=mm, second=0, microsecond=0)
    reminders = _load_reminders()
    reminders.append({"chat_id": chat_id, "at": target.isoformat(), "text": body or "(напоминание)"})
    _save_reminders(reminders)
    api.send_message(chat_id, f"⏰ Напомню {target.strftime('%d.%m %H:%M')}: «{body[:100]}»")


def _run_due_reminders() -> int:
    """Отправить созревшие напоминания (вызывается по таймеру и при старте бота)."""
    import urllib.request as _urllib
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("AIOS_TELEGRAM_TOKEN", "")
    reminders = _load_reminders()
    if not reminders:
        return 0
    now = datetime.now()
    due = [r for r in reminders if datetime.fromisoformat(r["at"]) <= now]
    if not due:
        return 0
    left = [r for r in reminders if datetime.fromisoformat(r["at"]) > now]
    for r in due:
        if not token:
            continue
        payload = json.dumps({"chat_id": r["chat_id"],
                              "text": f"⏰ <b>Напоминание</b>: {_esc_tg(r.get('text', ''))}",
                              "parse_mode": "HTML"}).encode()
        try:
            req = _urllib.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                  data=payload, headers={"Content-Type": "application/json"})
            with _urllib.urlopen(req, timeout=30):
                pass
            print(f"  [REMINDER] sent: {r.get('text', '')[:50]}")
        except Exception as e:
            print(f"  [REMINDER] err: {e}")
            left.append(r)  # попробуем ещё раз в следующий цикл
    _save_reminders(left)
    return len(due)


def _transcribe_audio(path: str) -> str:
    """Распознать голосовое через Gemini (inline audio). Возвращает текст или ''."""
    import base64
    import urllib.request as _urllib

    try:
        data_b64 = base64.b64encode(Path(path).read_bytes()).decode()
    except Exception:
        return ""

    keys = [os.environ.get("GEMINI_API_KEY", "")]
    for i in (1, 2, 3):
        keys.append(os.environ.get(f"GEMINI_API_KEY_{i}", ""))
    keys = [k for k in keys if k]

    mime = "audio/ogg" if path.lower().endswith((".ogg", ".oga", ".opus")) else "audio/mpeg"
    for model in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite",
                  "gemini-2.5-flash-lite", "gemini-flash-latest"):
        for key in keys:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                payload = json.dumps({
                    "contents": [{"parts": [
                        {"inline_data": {"mime_type": mime, "data": data_b64}},
                        {"text": "Распознай речь дословно. Верни только распознанный текст, без пояснений."},
                    ]}],
                }).encode()
                req = _urllib.Request(url, data=payload,
                                      headers={"Content-Type": "application/json"})
                with _urllib.urlopen(req, timeout=60) as resp:
                    out = json.loads(resp.read())
                cands = out.get("candidates") or []
                if cands:
                    txt = (cands[0].get("content", {}).get("parts") or [{}])[0].get("text", "").strip()
                    if txt:
                        return txt
            except Exception as e:
                print(f"  [VOICE] {model} err: {str(e)[:120]}")
                continue
    return ""


def _handle_account_intent(api, chat_id: int, text: str) -> bool:
    """Обработать «человеческое» сообщение про Google/Instagram. True = обработано."""
    t = text.lower()

    # 1) подтверждение/отмена ожидающего действия
    if chat_id in _pending_confirm:
        yes = any(w in t for w in ("да", "отправь", "отправляй", "подтверж", "yes", "ага", "го", "ок", "давай"))
        no = any(w in t for w in ("нет", "отмена", "не надо", "no", "cancel", "стоп", "не отправляй", "не хочу"))
        if yes or no:
            pend = _pending_confirm.pop(chat_id)
            kind = pend.get("kind", "")
            if no:
                api.send_message(chat_id, "🚫 Действие отменено.")
                return True
            if kind == "gmail":
                d = pend["data"]
                data = _run_account_control(["google", "gmail_send", "--to", d["to"],
                                             "--subject", d["subject"], "--body", d["body"],
                                             "--confirm"])
                if data.get("status") == "sent":
                    api.send_message(chat_id,
                                     f"✅ Письмо отправлено:\n📧 <b>{d['subject']}</b> → {d['to']}")
                else:
                    api.send_message(chat_id, f"❌ Ошибка отправки: {data.get('error', '?')}")
                return True
            if kind == "calendar_add":
                d = pend["data"]
                data = _run_account_control(["google", "calendar_add",
                                             "--title", d["title"], "--date", d.get("date", ""),
                                             "--time", d.get("time", ""), "--desc", d.get("desc", ""),
                                             "--confirm"])
                if data.get("status") == "ok":
                    api.send_message(chat_id,
                                     f"✅ Событие создано:\n📅 <b>{d['title']}</b>\n"
                                     f"🕐 {data.get('start', '')} → {data.get('end', '')}\n"
                                     f"🔗 {data.get('url', '')}")
                else:
                    api.send_message(chat_id, f"❌ Ошибка создания события: {data.get('error', '?')}")
                return True
            if kind == "ig_like":
                d = pend["data"]
                data = _run_account_control(["instagram", "like", d["url"], "--confirm"])
                st = data.get("status")
                if st == "liked":
                    api.send_message(chat_id, f"❤️ Лайк поставлен: {d['url']}")
                elif st == "already_liked":
                    api.send_message(chat_id, f"👍 Пост уже лайкнут: {d['url']}")
                else:
                    api.send_message(chat_id, f"❌ Ошибка: {data.get('error', st)}")
                return True
            if kind == "ig_unlike":
                d = pend["data"]
                data = _run_account_control(["instagram", "unlike", d["url"], "--confirm"])
                st = data.get("status")
                if st == "unliked":
                    api.send_message(chat_id, f"💔 Лайк убран: {d['url']}")
                else:
                    api.send_message(chat_id, f"ℹ️ {data.get('error', st)}")
                return True
            if kind == "ig_follow":
                d = pend["data"]
                data = _run_account_control(["instagram", "follow", d["username"],
                                             "--action", d.get("action", "follow"), "--confirm"])
                st = data.get("status")
                if st == "ok":
                    verb = "подписался на" if d.get("action") == "follow" else "отписался от"
                    api.send_message(chat_id, f"✅ {verb} @{d['username']}")
                else:
                    api.send_message(chat_id, f"ℹ️ {data.get('error', st)}")
                return True
            if kind == "gmail_reply":
                d = pend["data"]
                data = _run_account_control(["google", "gmail_reply", d["msg_id"], d["text"], "--confirm"])
                if data.get("status") == "sent":
                    api.send_message(chat_id,
                                     f"✅ Ответ на письмо №{d['idx']} отправлен:\n📧 {data.get('subject')} → {data.get('to')}")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', '?')}")
                return True
            if kind == "dm_send":
                d = pend["data"]
                data = _run_account_control(["instagram", "dm_send", d["thread"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"✅ Отправлено <b>{d['thread']}</b> в Direct: «{d['text'][:150]}»")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "dm_new":
                d = pend["data"]
                data = _run_account_control(["instagram", "dm_new", d["username"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"✅ Отправлено @{d['username']}: «{d['text'][:150]}»")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "viber_send":
                d = pend["data"]
                data = _run_account_control(["viber", "send", d["chat"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"✅ Отправлено в Viber <b>{d['chat']}</b>: «{d['text'][:150]}»")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "messenger_send":
                d = pend["data"]
                data = _run_account_control(["facebook", "messenger_send", d["chat"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"✅ Отправлено в Messenger <b>{d['chat']}</b>: «{d['text'][:150]}»")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "tg_send":
                d = pend["data"]
                data = _run_account_control(["tg", "send", d["ref"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"✅ Отправлено в Telegram <b>{d['ref']}</b>: «{d['text'][:150]}»")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "tg_bot":
                d = pend["data"]
                data = _run_account_control(["tg", "bot", d["bot"], d["command"], "--confirm"])
                st = data.get("status")
                if st == "ok":
                    reply = data.get("reply") or []
                    txt = f"🤖 <b>@{d['bot']}</b> ответил:\n" + "\n".join(
                        f"{'🤖' if not x.get('out') else '🙋'} {_esc_tg(x.get('text', ''))}" for x in reply[:3])
                    api.send_message(chat_id, txt)
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "tiktok_upload":
                d = pend["data"]
                data = _run_account_control(["tiktok", "upload", d["video"],
                                             "--caption", d.get("caption", ""), "--confirm"])
                st = data.get("status")
                if st == "published":
                    api.send_message(chat_id, "🎵 Видео опубликовано в TikTok!")
                elif st == "draft":
                    api.send_message(chat_id, f"⚠️ {data.get('note', 'загружено, но не опубликовано')}")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            api.send_message(chat_id, "❌ Неизвестный тип действия.")
            return True

    ig_words = ("инста", "instagram", "подписчик", "мой профиль в инст", "мой инст",
                "мои посты", "профиль инстаграм", "мой instagram", "сторис", "story",
                "лайк", "like", "подпиш", "отпиш", "подпис", "отпис", "follow",
                "unfollow", "истори", "директ", "direct", "сообщен", "переписк", "личн",
                "чат")
    g_words = ("почт", "gmail", "email", "письм", "календар", "calendar", "диск",
               "drive", "гугл", "google", "юху", "аккаунт гугл", "google аккаунт",
               "непрочитан", "кто я", "google", "событ", "расписан", "документ",
               "поиск", "найди", "недел", "файл", "скачай", "ответь", "прочитай письмо",
               "фейсбук", "facebook", "тикток", "tiktok", "олх", "olx", "объявлен",
               "контакт", "телефонная книга", "адресная книга", "пром", "prom.ua",
               "телеграм", "telegram", "в телеге", "нова пошт", "нова почт",
               "новая пошта", "nova poshta", "novaposhta", "ттн", "посилк",
               "посылк", "відділенн", "отделен")
    is_ig = any(w in t for w in ig_words)
    is_g = any(w in t for w in g_words)
    # Telegram userbot (личный аккаунт)
    tg_words = any(w in t for w in ("тг ", "телеграм", "telegram", "в телеге",
                                    "личный телеграм", "мой телеграм",
                                    "боту @", "команду боту", "команда боту"))
    other_words = ("вайбер", "вибер", "viber", "мессенджер", "messenger",
                   "опубликуй видео", "опубликуй ролик", "опубликуй в тикток",
                   "боту @", "команду боту", "команда боту",
                   "в телеге", "телеграм", "telegram", "тг",
                   "инбокс", "inbox", "все сообщения", "всё в одном", "сводка сообщений",
                   "где что новое", "проверь всё", "напомни", "напоминание",
                   "аналитик", "рост подписчик", "динамика", "статистика аккаунт",
                   "сколько прибавил", "тренд", "запланируй пост", "пост в тикток на",
                   "пост в инстаграм на", "расписание постов")
    is_other = any(w in t for w in other_words)
    if not is_ig and not is_g and not is_other and not tg_words:
        return False

    # ---- Instagram ----
    if is_ig and not tg_words:
        # ---- Direct (переписка) ----
        # «чат» без уточнения — DM только если речь не про Telegram
        is_dm = any(w in t for w in ("директ", "direct", "сообщен", "переписк",
                                     "чат в інст", "чат в инст", "личн")) or \
                ("чат" in t and "телеге" not in t and "телеграм" not in t
                 and "telegram" not in t and "тг" not in t)
        if is_dm:
            send_word = any(w in t for w in ("напиши", "отправь", "ответь", "написать",
                                             "reply", "напишіть", "відповісти"))
            read_word = any(w in t for w in ("прочитай", "покажи", "что в", "що в",
                                             "последние", "новые", "прочитать"))
            if send_word:
                body = ""
                target = ""
                m_colon = re.search(r":\s*(.+)$", text, re.IGNORECASE)
                if m_colon:
                    target = text[:m_colon.start()]
                    body = m_colon.group(1).strip()
                else:
                    rest = re.sub(
                        r"^(напиши|отправь|ответь|написать|скажи|напишіть|відповісти)"
                        r"(\s+(в|в\s+директ|директ|direct|личку|сообщение))?\s+",
                        "", text, flags=re.IGNORECASE)
                    rest = re.sub(r"^(в|в\s+директ|директ|direct|личку|сообщение)\s+",
                                  "", rest, flags=re.IGNORECASE)
                    parts = rest.split(None, 1)
                    if parts:
                        target = parts[0].strip(" ,.;:—–")
                        body = parts[1].strip() if len(parts) > 1 else ""
                target = re.sub(r"^(в|ответить|написать|сообщение|директ|direct)\s*",
                                "", target, flags=re.IGNORECASE).strip(" ,.;:—–")
                if not target or not body:
                    api.send_message(chat_id,
                                     "💬 <b>Директ</b>: напишите, например:\n"
                                     "«напиши в директ Серега: привет, как дела?»\n"
                                     "или «ответь в директ @username, текст»")
                    return True
                if target.startswith("@"):
                    _pending_confirm[chat_id] = {"kind": "dm_new",
                                                 "data": {"username": target.lstrip("@"),
                                                          "text": body}}
                    api.send_message(chat_id,
                                     f"💬 Новый чат с <b>@{target.lstrip('@')}</b>:\n"
                                     f"«{body[:200]}»\n\nПодтвердите: «да» / «нет»")
                else:
                    _pending_confirm[chat_id] = {"kind": "dm_send",
                                                 "data": {"thread": target, "text": body}}
                    api.send_message(chat_id,
                                     f"💬 Отправить <b>{target}</b> в Direct:\n"
                                     f"«{body[:200]}»\n\nПодтвердите: «да» / «нет»")
                return True
            if read_word:
                name = None
                m = re.search(r"(?:директ|чат|чате|чату|переписке|переписку|сообщениях)[\s,:—–]*([\w\sА-Яа-яЁёІіЇїЄє'’.-]{2,30}?)(?:[.!?]|$)",
                              text, re.IGNORECASE)
                if m:
                    cand = m.group(1).strip()
                    cand = re.sub(r"^(в|от|с|у|мне|мой|моем|новые|последние|прочитай|покажи)\s+", "", cand,
                                  flags=re.IGNORECASE).strip()
                    if len(cand) >= 2:
                        name = cand
                api.send_message(chat_id, "⏳ Открываю Direct…")
                data = _run_account_control(["instagram", "dm_read", name or "Серега Потуроев",
                                             "--limit", "12"])
                if data.get("status") == "ok":
                    msgs = data.get("messages") or []
                    if not msgs:
                        api.send_message(chat_id, "💬 В чате нет текстовых сообщений (только системные).")
                    else:
                        txt = "💬 <b>Последние сообщения</b>:\n" + "\n".join(
                            f"• {_esc_tg(m.get('text', ''))}" for m in msgs[-12:])
                        api.send_message(chat_id, txt)
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', '?')}")
                return True
            # просто «директ» — список чатов
            api.send_message(chat_id, "⏳ Загружаю Direct…")
            data = _run_account_control(["instagram", "dm_list", "10"])
            if data.get("status") == "ok":
                threads = data.get("threads") or []
                if not threads:
                    api.send_message(chat_id, "💬 В Direct пусто.")
                else:
                    txt = "💬 <b>Чаты Direct</b>:\n" + "\n".join(
                        f"• <b>{_esc_tg(x.get('name', '?'))}</b> — {_esc_tg(x.get('preview', ''))}"
                        for x in threads)
                    api.send_message(chat_id, txt)
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
            return True
        if any(w in t for w in ("сторис", "story", "истори")):
            api.send_message(chat_id,
                             "📤 <b>Сторис</b>: к сожалению, Instagram web не даёт создавать сторис "
                             "из браузера (проверено: кнопки «Create»/Story нет ни в desktop, ни в "
                             "mobile-версии). Сторис можно сделать только в мобильном приложении. "
                             "А вот лайки, подписки, посты — легко!")
            return True
        if any(w in t for w in ("лайк", "like")):
            urls = re.findall(r"https?://\S+", text) or re.findall(r"/p/[A-Za-z0-9_-]+", text)
            if not urls:
                api.send_message(chat_id,
                                 "❤️ <b>Лайк</b>: пришлите ссылку на пост, например:\n"
                                 "«лайкни https://www.instagram.com/p/CODE/»")
                return True
            url = urls[0] if urls[0].startswith("http") else f"https://www.instagram.com{urls[0]}"
            data = _run_account_control(["instagram", "like", url])
            st = data.get("status")
            if st == "already_liked":
                api.send_message(chat_id, "👍 Пост уже лайкнут.")
                return True
            if st == "need_confirm":
                _pending_confirm[chat_id] = {"kind": "ig_like", "data": {"url": url}}
                api.send_message(chat_id, f"❤️ Поставить лайк: {url}\nПодтвердите: «да» / «нет»")
                return True
            api.send_message(chat_id, f"❌ {data.get('error', st)}")
            return True
        if ("подпиши" in t or "отпиши" in t):
            action = "unfollow" if "отпиши" in t else "follow"
            m = re.search(r"@([a-zA-Z0-9_.]+)", text)
            uname = m.group(1) if m else None
            if not uname:
                for w in reversed(re.split(r"[\s,]+", t)):
                    w = w.strip("@")
                    if w and not any(k in w for k in ("подпиши", "отпиши", "подпишись", "отпишись",
                                                      "на", "от", "меня", "пожалуйста", "себя",
                                                      "надо", "нужно", "подпис", "отпис", "аккаунт")):
                        uname = w
                        break
            if not uname:
                api.send_message(chat_id,
                                 "👤 <b>Подписка</b>: укажите username, например\n"
                                 "«подпишись на @dawnrichard» или «отпишись от @ivan»")
                return True
            data = _run_account_control(["instagram", "follow", uname, "--action", action])
            st = data.get("status")
            if st in ("already_following", "not_following"):
                api.send_message(chat_id, f"ℹ️ @{uname}: {data.get('button', st)}")
                return True
            if st == "need_confirm":
                _pending_confirm[chat_id] = {"kind": "ig_follow",
                                             "data": {"username": uname, "action": action}}
                verb = "подписаться на" if action == "follow" else "отписаться от"
                api.send_message(chat_id, f"👤 {verb} @{uname}?\nПодтвердите: «да» / «нет»")
                return True
            api.send_message(chat_id, f"ℹ️ {data.get('error', st)}")
            return True
        if any(w in t for w in ("скрин", "покажи", "фото")):
            _acct_instagram(api, chat_id, "screenshot")
            return True
        if "пост" in t and "/p/" in text:
            m = re.search(r"/p/([A-Za-z0-9_-]+)", text)
            if m:
                data = _run_account_control(["instagram", "post", m.group(1)])
                if data.get("status") == "ok":
                    p = data.get("post", {})
                    txt = (f"🖼 <b>Пост {p.get('code')}</b>\n"
                           f"💬 {p.get('caption') or 'без подписи'}\n"
                           f"❤️ Лайки: {p.get('likes') or '?'}\n"
                           f"🔗 {p.get('url')}")
                    _acct_send_result(api, chat_id,
                                      {"status": "ok", "text": txt,
                                       "screenshot": data.get("screenshot"),
                                       "caption": "🖼 Пост"}, "")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', '?')}")
                return True
        if any(w in t for w in ("пост", "посты", "публикац")):
            _acct_instagram(api, chat_id, "posts")
            return True
        # профиль / статистика / «покажи инсту» / «мой инст»
        _acct_instagram(api, chat_id, "profile")
        return True

    # ---- Дайджест / сводка ----
    if any(w in t for w in ("дайджест", "утренний отчёт", "утренний отчет", "что нового",
                            "сводка", "сводку", "отчёт за день", "отчет за день",
                            "сводку за день", "итоги дня")):
        api.send_message(chat_id, "⏳ Собираю дайджест (почта + календарь + Instagram)…")
        import subprocess as _sp
        try:
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_digest.py"),
                         "--chat", str(chat_id)],
                        capture_output=True, text=True, timeout=200, cwd=str(PROJECT_ROOT))
            if "Дайджест отправлен" in (r.stdout or ""):
                api.send_message(chat_id, "✅ Дайджест отправлен ☀️")
            else:
                api.send_message(chat_id, "❌ Не удалось собрать дайджест: "
                                          f"{(r.stderr or r.stdout or '?')[-250:]}")
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка дайджеста: {e}")
        return True

    # ---- Планировщик постов ----
    if any(w in t for w in ("запланируй пост", "запланupyй пост", "пост в тикток на",
                            "пост в инстаграм на", "расписание постов")):
        platform = "tiktok" if "тикток" in t or "tiktok" in t else \
                   ("instagram" if "инстаграм" in t or "instagram" in t or "инст" in t else "tiktok")
        m_time = re.search(r"\b(\d{1,2})[:.](\d{2})\b", t)
        if not m_time:
            api.send_message(chat_id, "📅 Формат: «запланируй пост в тикток завтра в 18:00 описание»")
            return True
        hh, mm = int(m_time.group(1)), int(m_time.group(2))
        day_off = 1 if "завтра" in t else (2 if "послезавтра" in t else 0)
        target = datetime.now() + timedelta(days=day_off)
        target = target.replace(hour=hh, minute=mm, second=0, microsecond=0)
        text = re.sub(r"^(запланируй пост|пост)\s*(в\s+)?(тикток|tiktok|инстаграм|instagram|инст)?\s*(на)?\s*", "", t, flags=re.IGNORECASE)
        text = re.sub(r"\b\d{1,2}[:.]\d{2}\b", "", text).strip()
        text = re.sub(r"^(завтра|сегодня|послезавтра)\s*", "", text, flags=re.IGNORECASE).strip()
        video = _last_video.get(chat_id, "")
        # очередь
        qfile = PROJECT_ROOT / "data" / "posts_queue.json"
        try:
            q = json.loads(qfile.read_text(encoding="utf-8"))
        except Exception:
            q = []
        q.append({"platform": platform, "at": target.isoformat(), "text": text,
                  "chat_id": chat_id, "video": video})
        qfile.parent.mkdir(parents=True, exist_ok=True)
        qfile.write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")
        api.send_message(chat_id,
                         f"📅 Запланировано: {platform} {target.strftime('%d.%m %H:%M')}\n"
                         f"«{text[:100]}»\n"
                         f"{'🎬 Видео приложено — опубликуется автоматически' if video and platform == 'tiktok' else 'ℹ️ Придёт напоминание (видео не приложено или не TikTok)'}")
        return True

    # ---- TikTok upload ----
    if any(w in t for w in ("опубликуй видео", "опубликуй ролик", "загрузи видео в тикток",
                            "пости видео в тикток", "опубликуй в тикток")):
        caption = re.sub(r"(опубликуй видео|опубликуй ролик|загрузи видео в тикток|пости видео в тикток|опубликуй в тикток)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
        video = _last_video.get(chat_id)
        if not video:
            api.send_message(chat_id,
                             "🎬 Отправьте видео сюда, а потом напишите «опубликуй видео в тикток <описание>».")
            return True
        if not os.path.exists(video):
            api.send_message(chat_id, "❌ Сохранённое видео не найдено. Пришлите видео заново.")
            return True
        _pending_confirm[chat_id] = {"kind": "tiktok_upload",
                                     "data": {"video": video, "caption": caption}}
        api.send_message(chat_id,
                         f"🎬 <b>Публикация в TikTok</b>\n"
                         f"Файл: {os.path.basename(video)}\n"
                         f"Описание: «{caption[:200] or '—'}»\n\n"
                         f"Опубликовать? «да» / «нет» (риск: TikTok может запросить проверку)")
        return True

    # ---- Viber (десктоп) ----
    if any(w in t for w in ("вайбер", "вибер", "viber")):
        send_word = any(w in t for w in ("напиши", "отправь", "написать", "ответь"))
        read_word = any(w in t for w in ("прочитай", "покажи", "что в", "последние"))
        if send_word:
            m = re.search(r":\s*(.+)$", text, re.IGNORECASE)
            body = m.group(1).strip() if m else ""
            target = re.sub(r"^(напиши|отправь|написать|ответь)(\s+(в|в\s+вайбер|вайбер|viber|вибер))?\s+", "",
                            text, flags=re.IGNORECASE)
            target = re.sub(r"^(в|вайбер|viber|вибер)\s+", "", target, flags=re.IGNORECASE)
            target = target.split(":", 1)[0].strip(" ,.;:—–")
            if not target or not body:
                api.send_message(chat_id,
                                 "💬 <b>Viber</b>: напишите «напиши в вайбер <имя>: <текст>»")
                return True
            _pending_confirm[chat_id] = {"kind": "viber_send",
                                         "data": {"chat": target, "text": body}}
            api.send_message(chat_id,
                             f"💬 Отправить <b>{target}</b> в Viber:\n«{body[:200]}»\n\n«да» / «нет»")
            return True
        if read_word:
            m = re.search(r"(?:вайбер|viber|вибер)[\s,:—–]*([\w\sА-Яа-яЁёІіЇїЄє'’.-]{2,30}?)(?:[.!?]|$)", text, re.IGNORECASE)
            chat = m.group(1).strip() if m else ""
            api.send_message(chat_id, "⏳ Открываю Viber…")
            data = _run_account_control(["viber", "read", chat or "Viber"])
            if data.get("status") == "ok":
                msgs = data.get("messages") or []
                if not msgs:
                    api.send_message(chat_id, "💬 В чате нет распознанных сообщений (или пусто).")
                else:
                    api.send_message(chat_id, "💬 <b>Viber</b>:\n" + "\n".join(
                        f"• {_esc_tg(x.get('text', ''))}" for x in msgs[-12:]))
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
            return True
        # список чатов
        api.send_message(chat_id, "⏳ Читаю чаты Viber…")
        data = _run_account_control(["viber", "chats"])
        if data.get("status") == "ok":
            chats = data.get("chats") or []
            if chats:
                api.send_message(chat_id, "💬 <b>Чаты Viber</b>:\n" + "\n".join(
                    f"• {_esc_tg(c.get('name'))}" for c in chats[:20]))
            else:
                api.send_message(chat_id,
                                 "💬 Не нашёл чаты (возможно, Viber не залогинен — нужен QR-вход).")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- Messenger ----
    if any(w in t for w in ("мессенджер", "messenger", "фейсбук чат", "чат фейсбук")):
        send_word = any(w in t for w in ("напиши", "отправь", "написать", "ответь"))
        read_word = any(w in t for w in ("прочитай", "покажи", "что в", "последние"))
        if send_word:
            m = re.search(r":\s*(.+)$", text, re.IGNORECASE)
            body = m.group(1).strip() if m else ""
            target = re.sub(r"^(напиши|отправь|написать|ответь)(\s+(в|в\s+мессенджер|мессенджер|messenger))?\s+", "",
                            text, flags=re.IGNORECASE)
            target = re.sub(r"^(в|мессенджер|messenger)\s+", "", target, flags=re.IGNORECASE)
            target = target.split(":", 1)[0].strip(" ,.;:—–")
            if not target or not body:
                api.send_message(chat_id,
                                 "💬 <b>Messenger</b>: напишите «напиши в мессенджер <имя>: <текст>»")
                return True
            _pending_confirm[chat_id] = {"kind": "messenger_send",
                                         "data": {"chat": target, "text": body}}
            api.send_message(chat_id,
                             f"💬 Отправить <b>{target}</b> в Messenger:\n«{body[:200]}»\n\n«да» / «нет»")
            return True
        if read_word:
            m = re.search(r"(?:мессенджер|messenger)[\s,:—–]*([\w\sА-Яа-яЁёІіЇїЄє'’.-]{2,30}?)(?:[.!?]|$)", text, re.IGNORECASE)
            chat = m.group(1).strip() if m else ""
            api.send_message(chat_id, "⏳ Открываю Messenger…")
            data = _run_account_control(["facebook", "messenger_read", chat or "Chat", "--limit", "12"])
            if data.get("status") == "ok":
                msgs = data.get("messages") or []
                if not msgs:
                    api.send_message(chat_id, "💬 В чате нет сообщений.")
                else:
                    api.send_message(chat_id, "💬 <b>Messenger</b>:\n" + "\n".join(
                        f"• {_esc_tg(x.get('text', ''))}" for x in msgs[-12:]))
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
            return True
        api.send_message(chat_id, "⏳ Загружаю чаты Messenger…")
        data = _run_account_control(["facebook", "messenger_list", "--limit", "10"])
        if data.get("status") == "ok":
            chats = data.get("chats") or []
            if chats:
                api.send_message(chat_id, "💬 <b>Чаты Messenger</b>:\n" + "\n".join(
                    f"• {_esc_tg(c.get('name'))}" for c in chats[:10]))
            else:
                api.send_message(chat_id, "💬 Чатов не нашёл.")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- Facebook ----
    if any(w in t for w in ("фейсбук", "facebook", "фб", "fb ")) and not any(w in t for w in ("директ", "сообщен")):
        if any(w in t for w in ("лента", "новости", "новости", "посты", "пост", "feed")):
            api.send_message(chat_id, "⏳ Открываю ленту Facebook…")
            data = _run_account_control(["facebook", "feed", "5"])
            if data.get("status") == "ok":
                feed = data.get("feed") or []
                if feed:
                    txt = "📰 <b>Лента Facebook</b>:\n\n" + "\n\n".join(
                        f"• {_esc_tg(x.get('text', ''))[:300]}" for x in feed[:5])
                    api.send_message(chat_id, txt)
                else:
                    api.send_message(chat_id, "📰 Лента пуста (не удалось распарсить).")
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        else:
            api.send_message(chat_id, "⏳ Захожу в Facebook…")
            data = _run_account_control(["facebook", "profile"])
            if data.get("status") == "ok":
                f = data.get("facebook", {})
                txt = (f"📘 <b>Facebook</b>\n"
                       f"👤 Имя: {_esc_tg(f.get('name'))}\n"
                       f"🔗 {f.get('profile_url')}\n"
                       f"🔔 Уведомлений: {f.get('notifications') or 0}")
                _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                                 "screenshot": f.get("screenshot"),
                                                 "caption": "📘 Facebook"}, "")
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- TikTok ----
    if any(w in t for w in ("тикток", "tiktok", "тик ток", "тт ")):
        api.send_message(chat_id, "⏳ Захожу в TikTok…")
        data = _run_account_control(["tiktok", "profile"])
        if data.get("status") == "ok":
            p = data.get("tiktok", {})
            txt = (f"🎵 <b>TikTok</b>\n"
                   f"👤 Имя: {_esc_tg(p.get('name') or p.get('username'))}\n"
                   f"👥 Подписчики: {p.get('followers') or 0}\n"
                   f"🔄 Подписки: {p.get('following') or 0}\n"
                   f"❤️ Лайки: {p.get('likes') or 0}\n"
                   f"ℹ️ {_esc_tg(p.get('bio') or 'без описания')}\n"
                   f"🔗 {p.get('profile_url')}")
            _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                             "screenshot": p.get("screenshot"),
                                             "caption": "🎵 TikTok"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- Аналитика ----
    if any(w in t for w in ("аналитик", "рост подписчик", "динамика", "статистика аккаунт",
                            "сколько прибавил", "тренд")):
        api.send_message(chat_id, "⏳ Собираю аналитику (IG, TikTok, OLX)…")
        import subprocess as _sp
        # обновить снапшот прямо сейчас
        try:
            _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_analytics_snapshot.py")],
                    capture_output=True, text=True, timeout=240, cwd=str(PROJECT_ROOT))
        except Exception:
            pass
        # читаем историю
        hist = {}
        try:
            hist = json.loads((PROJECT_ROOT / "data" / "analytics_state.json").read_text(encoding="utf-8"))
        except Exception:
            pass
        if not hist:
            api.send_message(chat_id, "📊 Нет данных аналитики ещё. Соберу при следующем прогоне.")
            return True
        dates = sorted(hist.keys())
        today = dates[-1]
        cur = hist[today]
        # ищем точку 7 и 30 дней назад
        def _delta(key):
            vals = []
            for d in reversed(dates):
                v = hist[d].get(key)
                if v is not None:
                    vals.append((d, v))
            cur_v = cur.get(key)
            if not vals or cur_v is None:
                return None, None, None
            # первая запись не раньше, чем сегодня
            base = vals[-1] if len(vals) > 1 else vals[0]
            return cur_v, base[1], len(vals) - 1

        txt = [f"📊 <b>Аналитика на {today}</b>"]
        for label, key in (("👥 Instagram подписчики", "instagram_followers"),
                           ("🔄 Instagram подписки", "instagram_following"),
                           ("🎵 TikTok подписчики", "tiktok_followers"),
                           ("❤️ TikTok лайки", "tiktok_likes"),
                           ("🛒 OLX объявления", "olx_ads")):
            cur_v, base_v, n = _delta(key)
            if cur_v is None:
                continue
            line = f"{label}: <b>{cur_v}</b>"
            if base_v is not None and n and base_v != cur_v:
                d = cur_v - base_v
                arrow = "📈" if d > 0 else "📉"
                line += f" {arrow}{d:+d} (за {n} дн.)"
            txt.append(line)
        api.send_message(chat_id, "\n".join(txt))
        return True

    # ---- Единый инбокс ----
    if any(w in t for w in ("инбокс", "inbox", "все сообщения", "всё в одном",
                            "сводка сообщений", "где что новое", "проверь всё")):
        api.send_message(chat_id, "⏳ Собираю всё в одном (почта, TG, IG, Messenger, OLX)… Это может занять ~1-2 мин")
        parts = []
        # 1) почта (быстро, IMAP)
        try:
            g = _run_account_control(["google", "gmail_list", "4"])
            if g.get("status") == "ok" and g.get("emails"):
                lines = [f"✉️ <b>Почта</b> ({g.get('unread_total', 0)} непрочитанных):"]
                for e in g["emails"][:4]:
                    lines.append(f"  • {_esc_tg(e.get('subject', '?'))[:60]}")
                parts.append("\n".join(lines))
        except Exception:
            pass
        # 2) Telegram личка (userbot)
        try:
            tg = _run_account_control(["tg", "dialogs", "8"])
            if tg.get("status") == "ok" and tg.get("dialogs"):
                unread_d = [d for d in tg["dialogs"] if d.get("unread")]
                if unread_d:
                    lines = [f"✈️ <b>Telegram</b> ({len(unread_d)} чатов с новыми):"]
                    for d in unread_d[:5]:
                        lines.append(f"  • {_esc_tg(d.get('name'))} 🔴{d.get('unread')}")
                    parts.append("\n".join(lines))
        except Exception:
            pass
        # 3) Instagram Direct
        try:
            ig = _run_account_control(["instagram", "dm_list", "5"])
            if ig.get("status") == "ok" and ig.get("threads"):
                lines = ["📸 <b>Instagram Direct</b>:"]
                for d in ig["threads"][:5]:
                    lines.append(f"  • {_esc_tg(d.get('name'))} — {_esc_tg((d.get('preview') or '')[:40])}")
                parts.append("\n".join(lines))
        except Exception:
            pass
        # 4) Messenger
        try:
            ms = _run_account_control(["facebook", "messenger_list", "--limit", "5"])
            if ms.get("status") == "ok" and ms.get("chats"):
                lines = ["💬 <b>Messenger</b>:"]
                for c in ms["chats"][:5]:
                    lines.append(f"  • {_esc_tg(c.get('name'))[:60]}")
                parts.append("\n".join(lines))
        except Exception:
            pass
        # 5) OLX
        try:
            olx = _run_account_control(["olx", "profile"])
            if olx.get("status") == "ok":
                o = olx.get("olx", {})
                parts.append(f"🛒 <b>OLX</b>: {_esc_tg(o.get('name') or '?')} · объявлений: {o.get('ads_count') or 0}")
        except Exception:
            pass

        if not parts:
            api.send_message(chat_id, "📭 Везде пусто (или не удалось собрать).")
        else:
            api.send_message(chat_id, "📥 <b>Единый инбокс</b>\n\n" + "\n\n".join(parts)[:3900])
        return True

    # ---- Напоминания ----
    if re.match(r"^(напомни|напоминание|remind)", t):
        _handle_reminder(api, chat_id, text)
        return True

    # ---- Новая Пошта ----
    np_words = any(w in t for w in ("нова пошт", "нова почт", "новая пошта", "nova poshta",
                                    "novaposhta", "ттн", "посилк", "посылк", "відділенн",
                                    "отделен", "нової пошти", "новой почты"))
    if np_words:
        # авто-ТТН: 14-значное число в тексте = предложить отследить
        m_ttn_auto = re.search(r"\b(\d{14})\b", text)
        if m_ttn_auto and not any(w in t for w in ("отследи", "отследить", "статус", "где")):
            ttn = m_ttn_auto.group(1)
            api.send_message(chat_id,
                             f"📦 Вижу номер посылки <code>{ttn}</code>.\n"
                             f"Напишите «отследи посылку {ttn}» — покажу статус.")
            return True
        # отследить посылку
        m_ttn = re.search(r"(\d{8,14})", text)
        if m_ttn:
            ttn = m_ttn.group(1)
            phone = ""
            m_ph = re.search(r"(\+?380\d{9})", text)
            if m_ph:
                phone = m_ph.group(1)
            api.send_message(chat_id, f"⏳ Отслеживаю посылку {ttn}…")
            data = _run_account_control(["novaposhta", "track", ttn, "--phone", phone])
            if data.get("status") == "ok":
                if not data.get("found"):
                    api.send_message(chat_id, f"📦 <b>{ttn}</b>: посылку не найдено.")
                    return True
                det = data.get("details") or {}
                txt = (f"📦 <b>Новая Пошта · {ttn}</b>\n"
                       f"📍 Статус: <b>{_esc_tg(data.get('tracking_status'))}</b>\n"
                       f"🚚 Маршрут: {_esc_tg(det.get('sender') or '?')} → {_esc_tg(det.get('recipient') or '?')}\n"
                       f"📅 План: {_esc_tg(det.get('scheduled_delivery') or '?')}\n")
                evs = data.get("events") or []
                if evs:
                    txt += "\n🗂 История:\n" + "\n".join(
                        f"• {_esc_tg(e.get('date'))} — {_esc_tg(e.get('event'))}"
                        f"{_esc_tg(' (' + e.get('settlement') + ')') if e.get('settlement') else ''}"
                        for e in evs[-5:])
                api.send_message(chat_id, txt[:3900])
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
            return True
        # отделения
        if any(w in t for w in ("відділенн", "отделен", "отделение")):
            q = re.sub(r"(найди|найти|покажи|отделен\w*|відділенн\w*|где|де)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
            if not q:
                api.send_message(chat_id, "🏢 Напишите «отделение Новой Пошты <город/адрес>»")
                return True
            api.send_message(chat_id, "⏳ Ищу отделения…")
            data = _run_account_control(["novaposhta", "offices", q])
            if data.get("status") == "ok":
                offs = data.get("offices") or []
                if offs:
                    api.send_message(chat_id, "🏢 <b>Отделения:</b>\n" + "\n".join(
                        f"• {_esc_tg(o)}" for o in offs[:8]))
                else:
                    api.send_message(chat_id, f"🏢 Отделения «{q}» не найдены.")
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
            return True
        # кабинет
        api.send_message(chat_id, "⏳ Открываю кабинет Новой Пошты…")
        data = _run_account_control(["novaposhta", "account"])
        if data.get("status") == "ok":
            txt = (f"📦 <b>Новая Пошта — кабинет</b>\n"
                   f"👤 {_esc_tg(data.get('name') or '?')}\n"
                   f"💰 Баланс: {_esc_tg(data.get('balance') or '—')} грн")
            _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                             "screenshot": data.get("screenshot"),
                                             "caption": "📦 Новая Пошта"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- Prom.ua ----
    if any(w in t for w in ("пром", "prom.ua", "пром юа")):
        api.send_message(chat_id, "⏳ Захожу в Prom…")
        data = _run_account_control(["prom", "profile"])
        if data.get("status") == "ok":
            txt = (f"🏪 <b>Prom.ua</b>\n"
                   f"🏬 Магазин: {_esc_tg(data.get('shop') or '?')}\n"
                   f"📦 Товаров: {data.get('products') or '?'}\n"
                   f"📋 Заказов: {data.get('orders') or '?'}")
            _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                             "screenshot": data.get("screenshot"),
                                             "caption": "🏪 Prom"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- Telegram (личный аккаунт, userbot) ----
    if tg_words:
        is_dialog = any(w in t for w in ("чаты", "диалог", "список чатов", "прочитай",
                                         "напиши", "отправь", "боту", "команду боту"))
        if any(w in t for w in ("напиши", "отправь")) and "боту" not in t:
            m = re.search(r":\s*(.+)$", text, re.IGNORECASE)
            body = m.group(1).strip() if m else ""
            target = re.sub(r"^(напиши|отправь)(\s+(в|в\s+телеграм|телеграм|telegram|тг))?\s+", "",
                            text, flags=re.IGNORECASE)
            target = re.sub(r"^(в|телеграм|telegram|тг)\s+", "", target, flags=re.IGNORECASE)
            target = target.split(":", 1)[0].strip(" ,.;:—–")
            if not target or not body:
                api.send_message(chat_id,
                                 "✈️ <b>Telegram</b>: «напиши в телеграм <имя>: <текст>»\n"
                                 "или «напиши боту @username: <команда>»")
                return True
            _pending_confirm[chat_id] = {"kind": "tg_send",
                                         "data": {"ref": target, "text": body}}
            api.send_message(chat_id,
                             f"✈️ Отправить <b>{target}</b> в Telegram:\n«{body[:200]}»\n\n«да» / «нет»")
            return True
        if "боту" in t or (any(w in t for w in ("бот ", "команду боту"))):
            m = re.search(r"@([a-zA-Z0-9_]+)", text)
            bot = m.group(1) if m else None
            command = re.sub(r"^(напиши|отправь|команду)\s+боту\s*@?\w*:?\s*", "", text, flags=re.IGNORECASE).strip()
            if not bot or not command:
                api.send_message(chat_id,
                                 "🤖 <b>Команда боту</b>: «напиши боту @BotFather /start»")
                return True
            _pending_confirm[chat_id] = {"kind": "tg_bot",
                                         "data": {"bot": bot, "command": command}}
            api.send_message(chat_id,
                             f"🤖 Отправить боту <b>@{bot}</b> команду «{command[:150]}»?\n\n«да» / «нет»")
            return True
        # диалоги / чтение
        if any(w in t for w in ("прочитай", "покажи чат", "что в чате")):
            m = re.search(r"(?:телеграм|телеге|тг|чате|чату)[\s,:—–]*([\w\sА-Яа-яЁёІіЇїЄє'’.-]{2,30}?)(?:[.!?]|$)", text, re.IGNORECASE)
            ref = m.group(1).strip() if m else ""
            api.send_message(chat_id, "⏳ Читаю Telegram…")
            data = _run_account_control(["tg", "read", ref or "Saved Messages", "--limit", "12"])
            if data.get("status") == "ok":
                msgs = data.get("messages") or []
                if not msgs:
                    api.send_message(chat_id, "✈️ В чате нет сообщений.")
                else:
                    api.send_message(chat_id, "✈️ <b>Telegram</b>:\n" + "\n".join(
                        f"{'👤' if not x.get('out') else '🙋'} {_esc_tg(x.get('text', ''))}" for x in msgs[-12:]))
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
            return True
        api.send_message(chat_id, "⏳ Загружаю чаты Telegram…")
        data = _run_account_control(["tg", "dialogs", "15"])
        if data.get("status") == "ok":
            dialogs = data.get("dialogs") or []
            if dialogs:
                txt = "✈️ <b>Последние чаты Telegram</b>:\n" + "\n".join(
                    f"• {_esc_tg(d.get('name'))}{' 🤖' if d.get('is_bot') else ''}"
                    f"{' 🔴' + str(d.get('unread')) if d.get('unread') else ''}"
                    for d in dialogs[:15])
                api.send_message(chat_id, txt)
            else:
                api.send_message(chat_id, "✈️ Чатов нет. Проверьте вход: нужен TG_API_ID/TG_API_HASH.")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- OLX ----
    if any(w in t for w in ("олх", "olx", "объявлен", "объявлени")):
        api.send_message(chat_id, "⏳ Захожу в OLX…")
        data = _run_account_control(["olx", "profile"])
        if data.get("status") == "ok":
            o = data.get("olx", {})
            txt = (f"🛒 <b>OLX</b>\n"
                   f"👤 Имя: {_esc_tg(o.get('name') or '?')}\n"
                   f"📄 Объявлений: {o.get('ads_count') or 0}\n"
                   f"💰 Баланс: {o.get('balance') or 0} грн\n"
                   f"🔑 Логин: {o.get('login')}")
            _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                             "screenshot": o.get("screenshot"),
                                             "caption": "🛒 OLX"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- Google Contacts ----
    if any(w in t for w in ("контакт", "телефонная книга", "адресная книга")):
        if any(w in t for w in ("добавь", "создай", "новый контакт", "запиши контакт")):
            m_name = re.search(r"контакт\s+([\w\sА-Яа-яЁёІіЇїЄє'’.-]{2,40}?)(?:\s+email\s+([\w.+-]+@[\w-]+\.[\w.]+))?(?:\s+тел[а-я]*\s*([+\d][\d\s().-]{5,})|$)", text, re.IGNORECASE)
            name = m_name.group(1).strip() if m_name else ""
            email = m_name.group(2) if m_name and m_name.group(2) else ""
            phone = m_name.group(3) if m_name and m_name.group(3) else ""
            if not name:
                api.send_message(chat_id,
                                 "👤 <b>Добавление контакта</b>: напишите, например\n"
                                 "«добавь контакт Иван Иванов email ivan@mail.com тел +380501112233»")
                return True
            api.send_message(chat_id, "⏳ Создаю контакт…")
            data = _run_account_control(["google", "contacts_add", "--name", name,
                                         "--email", email, "--phone", phone])
            if data.get("status") == "ok":
                api.send_message(chat_id, f"✅ Контакт <b>{name}</b> создан в Google Контактах.")
            else:
                api.send_message(chat_id, f"⚠️ {data.get('note', data.get('error', '?'))}")
            return True
        if any(w in t for w in ("найди", "поиск", "найди контакт")):
            q = re.sub(r"(найди|поиск|контакт)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
            q = re.sub(r"^(в|по)\s+", "", q).strip()
            if not q:
                api.send_message(chat_id, "👤 Напишите «найди контакт <имя>»")
                return True
            api.send_message(chat_id, "⏳ Ищу контакт…")
            data = _run_account_control(["google", "contacts_search", q])
            if data.get("status") == "ok":
                cons = data.get("contacts") or []
                if cons:
                    txt = "👤 <b>Найдено:</b>\n" + "\n".join(
                        f"• {_esc_tg(c.get('name'))} {_esc_tg('(' + c.get('email') + ')') if c.get('email') else ''}"
                        for c in cons[:8])
                    api.send_message(chat_id, txt)
                else:
                    api.send_message(chat_id, f"👤 Контакт «{q}» не найден.")
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
            return True
        # просто «контакты»
        api.send_message(chat_id, "⏳ Загружаю контакты…")
        data = _run_account_control(["google", "contacts_list", "--limit", "15"])
        if data.get("status") == "ok":
            cons = data.get("contacts") or []
            txt = f"👤 <b>Google Контакты</b> ({data.get('count') or len(cons)}):\n" + "\n".join(
                f"• {_esc_tg(c.get('name'))}" for c in cons[:15])
            _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                             "screenshot": data.get("screenshot"),
                                             "caption": "👤 Контакты"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- Google ----
    if any(w in t for w in ("кто я", "какой аккаунт", "кто залогинен")):
        _acct_google(api, chat_id, "whoami")
        return True
    if "непрочитан" in t:
        _acct_google(api, chat_id, "unread")
        return True
    if any(w in t for w in ("события", "событий", "расписание", "что в календаре", "что у меня в календаре", "план на день")):
        _acct_google(api, chat_id, "events")
        return True
    if any(w in t for w in ("добавь событие", "добавь в календарь", "создай событие", "запиши в календарь", "новое событие", "создать событие", "добавь встречу", "создай встречу")):
        parsed = _llm_extract_calendar(text)
        title = (parsed.get("title") or "").strip()
        if not title:
            api.send_message(chat_id,
                             "📅 <b>Создание события</b>: напишите, например:\n"
                             "«событие Встреча с Мишей завтра в 14:00»")
            return True
        date = (parsed.get("date") or "").strip()
        time_str = (parsed.get("time") or "").strip()
        desc = (parsed.get("desc") or "").strip()
        data = _run_account_control(["google", "calendar_add", "--title", title,
                                     "--date", date, "--time", time_str, "--desc", desc])
        if data.get("status") == "need_confirm":
            _pending_confirm[chat_id] = {"kind": "calendar_add",
                                         "data": {"title": title, "date": date,
                                                  "time": time_str, "desc": desc}}
            api.send_message(chat_id,
                             f"📅 <b>Подтвердите создание события:</b>\n{title}\n"
                             f"🕐 {data.get('start', date + ' ' + time_str)} → {data.get('end', '')}\n\n"
                             f"«да» — создать, «нет» — отмена")
            shot = data.get("screenshot")
            if shot and os.path.exists(shot):
                try:
                    api.send_photo(chat_id, shot, caption="📅 Предпросмотр")
                except Exception:
                    pass
            return True
        api.send_message(chat_id, f"❌ {data.get('error', 'ошибка')}")
        return True
    if any(w in t for w in ("найди письмо", "найди письма", "поиск в почте", "поиск писем", "поищи", "найди в почте", "найди на почте")):
        q = text
        for w in ("найди письмо", "найди письма", "поиск в почте", "поиск писем",
                  "поищи", "найди в почте", "найди на почте", "найди", "письма"):
            if w.lower() in q.lower():
                q = q.replace(w, "", 1)
        q = q.strip(" :,;—–«»\"'().")
        q = re.sub(r"^(от|по|про|на|в|о|из)\s+", "", q).strip()
        if not q:
            api.send_message(chat_id,
                             "🔍 <b>Поиск в почте</b>: напишите «найди письмо <запрос>»,\n"
                             "например «найди письмо от github»")
            return True
        data = _run_account_control(["google", "gmail_search", q, "5"])
        if data.get("status") == "ok":
            _last_gmail_ids[chat_id] = [e.get("id", "") for e in data.get("emails", [])]
            if data.get("emails"):
                api.send_message(chat_id, _fmt_gmail_list(data))
            else:
                api.send_message(chat_id, f"🔍 По запросу «{q}» писем не найдено.")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True
    if any(w in t for w in ("прочитай письмо", "прочитай писмо", "открой письмо",
                            "открой писмо", "покажи письмо", "покажи писмо")):
        m = re.search(r"письм[оае]?\s*№?\s*(\d+)", text, re.IGNORECASE)
        idx = int(m.group(1)) if m else 1
        ids = _last_gmail_ids.get(chat_id) or []
        if not ids:
            # загрузим последние
            data = _run_account_control(["google", "gmail_list", "5"])
            if data.get("status") == "ok":
                ids = [e.get("id", "") for e in data.get("emails", [])]
                _last_gmail_ids[chat_id] = ids
        if not ids or idx < 1 or idx > len(ids):
            api.send_message(chat_id, "❌ Сначала покажите письма («проверь почту»), потом номер.")
            return True
        api.send_message(chat_id, "⏳ Читаю письмо…")
        data = _run_account_control(["google", "gmail_read", ids[idx - 1], "--max", "3000"])
        if data.get("status") == "ok":
            txt = (f"📧 <b>{_esc_tg(data.get('subject'))}</b>\n"
                   f"✉️ {_esc_tg(data.get('from'))}\n"
                   f"🕐 {_esc_tg(data.get('date'))}\n\n"
                   f"{_esc_tg(data.get('body'))[:2500]}")
            api.send_message(chat_id, txt)
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True
    if any(w in t for w in ("ответь на письмо", "ответь на писмо", "напиши ответ на письмо",
                            "ответить на письмо")):
        m = re.search(r"письм[оае]?\s*№?\s*(\d+)", text, re.IGNORECASE)
        idx = int(m.group(1)) if m else 1
        ids = _last_gmail_ids.get(chat_id) or []
        body = ""
        m_colon = re.search(r":\s*(.+)$", text, re.IGNORECASE)
        if m_colon:
            body = m_colon.group(1).strip()
        if not ids or idx < 1 or idx > len(ids):
            api.send_message(chat_id, "❌ Сначала покажите письма, потом номер.")
            return True
        if not body:
            api.send_message(chat_id, "❌ Напишите текст ответа после двоеточия:\n"
                                      "«ответь на письмо 1: привет, получил, спасибо»")
            return True
        _pending_confirm[chat_id] = {"kind": "gmail_reply",
                                     "data": {"msg_id": ids[idx - 1], "idx": idx, "text": body}}
        api.send_message(chat_id,
                         f"📧 Ответ на письмо №{idx}:\n«{body[:200]}»\n\nОтправить? «да» / «нет»")
        return True
    if any(w in t for w in ("неделю", "план на неделю", "события на неделю",
                            "что на неделе", "на неделе")):
        api.send_message(chat_id, "⏳ Смотрю неделю в календаре…")
        data = _run_account_control(["google", "calendar_week"])
        if data.get("status") == "ok":
            evs = data.get("events") or []
            if evs:
                txt = "📅 <b>События на неделю:</b>\n" + "\n".join(f"• {_esc_tg(x)}" for x in evs)
            else:
                txt = "📅 На этой неделе событий нет."
            _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                             "screenshot": data.get("screenshot"),
                                             "caption": "📅 Неделя"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True
    if any(w in t for w in ("файлы на диске", "что на диске", "список диска",
                            "файлы в гугл диске", "файлы на гугл диске", "диск список",
                            "что в гугл диске", "что в google drive")):
        api.send_message(chat_id, "⏳ Загружаю Google Диск…")
        data = _run_account_control(["google", "drive_list", "--limit", "15"])
        if data.get("status") == "ok":
            files = data.get("files") or []
            if files:
                txt = "🗂 <b>Google Диск</b>:\n" + "\n".join(f"• {_esc_tg(f.get('title'))}" for f in files)
            else:
                txt = "🗂 На диске пусто."
            _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                             "screenshot": data.get("screenshot"),
                                             "caption": "🗂 Диск"}, "")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True
    if any(w in t for w in ("скачай файл", "скачай с диска", "загрузи файл с диска",
                            "скинь файл", "скачай")):
        ref = text
        for w in ("скачай файл", "скачай с диска", "загрузи файл с диска", "скинь файл",
                  "скачай", "файл"):
            if w.lower() in ref.lower():
                ref = ref.replace(w, "", 1)
        ref = ref.strip(" :,;—–«»\"'().")
        if not ref:
            api.send_message(chat_id, "🗂 Скажите, какой файл скачать:\n«скачай файл <имя или id>»")
            return True
        api.send_message(chat_id, "⏳ Скачиваю с Диска…")
        data = _run_account_control(["google", "drive_download", ref])
        if data.get("status") == "ok":
            path = data.get("path")
            name = data.get("name") or "файл"
            if path and os.path.exists(path):
                try:
                    api.send_document(chat_id, path, caption=f"🗂 {name}")
                except Exception as e:
                    api.send_message(chat_id, f"✅ Скачал, но не смог отправить файл: {e}")
            else:
                api.send_message(chat_id, f"✅ Скачал ({data.get('size', '?')} байт), файл: {path}")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True
    if any(w in t for w in ("создай документ", "новый документ", "сделай документ", "гугл документ", "документ в гугле", "создай гугл док")):
        parsed = _llm_extract_gmail(text)
        title = (parsed.get("subject") or "").strip()
        content = (parsed.get("body") or "").strip()
        if not title:
            m = re.search(r"документ\s+([\w\s-]{2,60}?)(?:[,.;]|$)", text, re.IGNORECASE)
            if m:
                title = m.group(1).strip()
        api.send_message(chat_id, "⏳ Создаю документ…")
        data = _run_account_control(["google", "docs_create", "--title", title, "--content", content])
        if data.get("status") == "ok":
            api.send_message(chat_id, f"📄 <b>Документ создан</b>:\n🔗 {data.get('url')}")
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True
    if any(w in t for w in ("календар", "calendar")):
        _acct_google(api, chat_id, "calendar")
        return True
    if any(w in t for w in ("диск", "drive", "файл")):
        _acct_google(api, chat_id, "drive")
        return True
    if any(w in t for w in ("отправ", "напиши письмо", "создай письмо")):
        # извлечь параметры через LLM
        parsed = _llm_extract_gmail(text)
        to = (parsed.get("to") or "").strip()
        if not to:
            api.send_message(chat_id, "❌ Не нашёл адрес получателя. Напишите, например: "
                                      "«отправь письмо ivan@gmail.com, тема Встреча, текст: привет»")
            return True
        subject = (parsed.get("subject") or "").strip() or "(без темы)"
        body = (parsed.get("body") or "").strip()
        _pending_confirm[chat_id] = {"kind": "gmail",
                                     "data": {"to": to, "subject": subject, "body": body}}
        api.send_message(chat_id,
                         f"📧 Готово к отправке:\n📮 Кому: {to}\n📝 Тема: {subject}\n"
                         f"💬 Текст: {body[:200]}\n\n"
                         f"Отправить? Напишите «да» — или «нет» для отмены.")
        return True
    if any(w in t for w in ("почт", "gmail", "email", "письм")):
        _acct_google(api, chat_id, "list")
        return True
    # по умолчанию — показать меню аккаунтов
    api.send_message(chat_id,
                     "🌐 Управление аккаунтами:\n"
                     "• Google: «проверь почту», «непрочитанные», «кто я», «календарь», «диск», «отправь письмо …»\n"
                     "• Instagram: «мой инстаграм», «мои посты», «скрин профиля»",
                     reply_markup=ACCOUNTS_MENU_KEYBOARD)
    return True


def cmd_accounts() -> str:
    return ("🌐 <b>Управление аккаунтами</b>\n\n"
            "Можно просто написать обычным текстом, например:\n"
            "• «проверь мою почту» / «сколько непрочитанных» / «найди письмо …»\n"
            "• «кто я в гугле» · «события на сегодня» · «добавь событие …»\n"
            "• «создай документ …» · «покажи календарь» · «отправь письмо …»\n"
            "• «мой инстаграм» · «директ» · «лайкни <ссылка>»\n"
            "• «покажи фейсбук» · «тикток» · «олх» / «мои объявления»\n"
            "• «подпишись на @…» / «отпишись от @…»\n\n"
            "Или выберите раздел:")


def cmd_google(args: str) -> str:
    a = args.strip().lower()
    if not a:
        return ("🌐 <b>Google</b>\n\nКоманды:\n"
                "/google whoami · /google unread · /google list\n"
                "/google search <запрос> · /google calendar · /google drive\n"
                "/google events · /google mailshot · /google send\n"
                "Или просто напишите «проверь почту», «события на сегодня», «создай документ …»")
    return "🌐 Google: укажите подкоманду."


def cmd_instagram(args: str) -> str:
    a = args.strip().lower()
    if not a:
        return ("📸 <b>Instagram</b>\n\nКоманды:\n"
                "/instagram profile · /instagram posts · /instagram screenshot\n"
                "Или просто напишите «мой инстаграм», «лайкни <ссылка>», «подпишись на @…»")
    return "📸 Instagram: укажите подкоманду."


# ---------------------------------------------------------------------------
# Coder commands — MetaCognitiveCoder integration
# ---------------------------------------------------------------------------


_coder_mod = None

def _get_coder_module():
    """Load MetaCognitiveCoder module."""
    global _coder_mod
    if _coder_mod is not None:
        return _coder_mod
    import importlib.util, sys
    mod_name = "aios_core.meta_cognitive_self_coder"
    spec = importlib.util.spec_from_file_location(
        mod_name, str(PROJECT_ROOT / "aios_core" / "meta_cognitive_self_coder.py")
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__name__ = mod_name
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    _coder_mod = mod
    return mod


@_safe
def cmd_coder_status() -> str:
    mod = _get_coder_module()
    coder = mod.MetaCognitiveCoder(mod.CoderConfig.from_env())
    s = coder.status()
    lines = []
    lines.append("🧠 <b>MetaCognitiveCoder v" + str(s.get("version", "?")) + "</b>")
    lines.append("")
    lines.append("  🤖 Модель: <code>" + str(s.get("llm_model", "?")) + "</code>")
    api_status = "✅ настроен" if s.get("llm_configured") else "❌ нет ключа"
    lines.append("  🔑 API: " + api_status)
    lines.append("  📁 Репозиторий: <code>" + str(s.get("repo_path", "?")) + "</code>")
    lines.append("  📝 Изменений: " + str(s.get("changes_made", 0)))
    lines.append("  🔄 Auto-commit: " + ("✅" if s.get("auto_commit") else "❌"))
    lines.append("  🚀 Auto-push: " + ("✅" if s.get("auto_push") else "❌"))
    return "\n".join(lines)


@_safe
def cmd_code_generate(args: str) -> str:
    if not args.strip():
        return "ℹ️ Использование: <code>/code Generate a function that...</code>"
    mod = _get_coder_module()
    coder = mod.MetaCognitiveCoder(mod.CoderConfig.from_env())
    change = coder.generate_code(args.strip())
    safe_status = "✅ Безопасно" if change.safe else "⚠️ Опасно"
    warn_list = change.warnings if change.warnings else ["Нет"]
    code_preview = change.new_code[:300].replace("<", "&lt;").replace(">", "&gt;")
    lines = []
    lines.append("🧠 <b>Код сгенерирован</b>")
    lines.append("")
    lines.append("  Безопасность: " + safe_status)
    lines.append("  Предупреждения:")
    for w in warn_list:
        lines.append("    • " + str(w))
    lines.append("")
    lines.append("<b>Код</b> (" + str(len(change.new_code)) + " символов):")
    lines.append("<pre>" + code_preview + "...</pre>")
    return "\n".join(lines)


@_safe
def cmd_code_review(args: str) -> str:
    file_path = args.strip()
    if not file_path:
        return "ℹ️ Использование: <code>/review run_telegram_bot.py</code>"
    mod = _get_coder_module()
    coder = mod.MetaCognitiveCoder(mod.CoderConfig.from_env())
    review = coder.review_code(file_path)
    lines = []
    lines.append("📋 <b>Code Review: " + file_path + "</b>")
    lines.append("")
    lines.append(review[:3500])
    return "\n".join(lines)


@_safe
def cmd_code_fix(args: str) -> str:
    parts = args.strip().split(maxsplit=1)
    if len(parts) < 2:
        return "ℹ️ Использование: <code>/fix file.py описание бага или traceback</code>"
    file_path, bug_desc = parts
    mod = _get_coder_module()
    coder = mod.MetaCognitiveCoder(mod.CoderConfig.from_env())
    change = coder.fix_bug(file_path, bug_desc)
    safe_status = "✅ Исправлено" if change.safe else "⚠️ Ошибка безопасности"
    lines = []
    lines.append("🔧 <b>Bug Fix: " + file_path + "</b>")
    lines.append("")
    lines.append("  Статус: " + safe_status)
    lines.append("  Предупреждения: " + str(change.warnings or "Нет"))
    lines.append("  Размер кода: " + str(len(change.new_code)) + " символов")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main polling loop
# ---------------------------------------------------------------------------


def parse_command(text: str) -> tuple[str, str]:
    """Split '/command args' into (command, args)."""
    text = (text or "").strip()
    if not text:
        return "", ""
    parts = text.split(maxsplit=1)
    cmd = parts[0].split("@")[0]  # strip @botname
    args = parts[1] if len(parts) > 1 else ""
    return cmd, args


# State storage for callback interactions (chat_id -> pending action)
_pending_actions: dict[int, str] = {}
_pending_confirmations: dict[int, str] = {}
DANGEROUS_CALLBACKS = {"coder_git_push", "coder_restart", "bot_restart", "bot_stop"}
_paused = False
_chat_history: dict[int, list[dict]] = {}  # chat_id -> message history
MAX_HISTORY = 20  # keep last 20 messages per chat


def _handle_button(api: TelegramAPI, chat_id: int, data: str) -> None:
    """Handle a callback, requiring an explicit second click for dangerous actions."""
    if data in DANGEROUS_CALLBACKS:
        _pending_confirmations[chat_id] = data
        api.send_message(
            chat_id,
            "⚠️ <b>Подтвердите опасное действие</b>",
            reply_markup={"inline_keyboard": [[
                {"text": "✅ Подтвердить", "callback_data": "confirm_dangerous"},
                {"text": "✖️ Отмена", "callback_data": "cancel_dangerous"},
            ]]},
        )
        return
    if data == "cancel_dangerous":
        _pending_confirmations.pop(chat_id, None)
        api.send_message(chat_id, "Действие отменено.")
        return
    if data == "confirm_dangerous":
        data = _pending_confirmations.pop(chat_id, "")
        if not data:
            api.send_message(chat_id, "Нет ожидающего действия для подтверждения.")
            return
    try:
        _handle_button_inner(api, chat_id, data)
    except Exception as e:
        print(f"  [BTN CRASH] {data}: {e}")
        import traceback; traceback.print_exc()
        try:
            api.send_message(chat_id, "Error: " + str(e)[:200])
        except:
            pass

def _handle_button_inner(api: TelegramAPI, chat_id: int, data: str) -> None:
    reply = None
    keyboard = None

    if data == "system_health":
        reply = cmd_system_health()
    elif data == "last_backup":
        reply = cmd_last_backup()
    elif data == "alert_history":
        reply = cmd_alert_history()
    elif data == "menu_back":
        reply = chr(127899) + " <b>AIOS Control Panel</b>" + chr(10) + chr(10) + chr(129504) + " Koder 24/7"
        keyboard = MAIN_MENU_KEYBOARD
    elif data == "menu_stats":
        reply = cmd_stats()
    elif data == "menu_platforms":
        reply = cmd_platforms()
    elif data == "menu_help":
        reply = cmd_help()
    elif data == "menu_coder":
        reply = chr(129504) + " <b>Koder</b>" + chr(10) + chr(10) + "Vyberite deistvie:"
        keyboard = CODER_MENU_KEYBOARD
    elif data == "menu_olx":
        reply = chr(128722) + " <b>OLX</b>"
        keyboard = OLX_MENU_KEYBOARD
    elif data == "menu_accounts":
        reply = cmd_accounts()
        keyboard = ACCOUNTS_MENU_KEYBOARD
    elif data == "accounts_google":
        reply = "🌐 <b>Google аккаунт</b> (jo.talbot@gmail.com)\n\nВыберите действие — или просто напишите «проверь почту» / «покажи календарь»."
        keyboard = GOOGLE_MENU_KEYBOARD
    elif data == "accounts_instagram":
        reply = "📸 <b>Instagram</b> (@jo.talbot)\n\nВыберите действие — или просто напишите «мой инстаграм» / «мои посты»."
        keyboard = INSTAGRAM_MENU_KEYBOARD
    elif data == "accounts_back":
        reply = cmd_accounts()
        keyboard = ACCOUNTS_MENU_KEYBOARD
    elif data == "accounts_facebook":
        reply = None
        keyboard = None
        api.send_message(chat_id, "⏳ Facebook…")
        _run_acct_cmd(api, chat_id, ["facebook", "profile"], "facebook")
    elif data == "accounts_tiktok":
        reply = None
        keyboard = None
        api.send_message(chat_id, "⏳ TikTok…")
        _run_acct_cmd(api, chat_id, ["tiktok", "profile"], "tiktok")
    elif data == "accounts_olx":
        reply = None
        keyboard = None
        api.send_message(chat_id, "⏳ OLX…")
        _run_acct_cmd(api, chat_id, ["olx", "profile"], "olx")
    elif data == "google_whoami":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "whoami")
    elif data == "google_unread":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "unread")
    elif data == "google_list":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "list")
    elif data == "google_calendar":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "calendar")
    elif data == "google_drive":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "drive")
    elif data == "google_mailshot":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "mailshot")
    elif data == "google_events":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "events")
    elif data == "google_event_add":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "event_prompt")
    elif data == "google_search":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "search_prompt")
    elif data == "google_docs":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "docs_prompt")
    elif data == "google_send":
        reply = None
        keyboard = None
        _acct_google(api, chat_id, "send_prompt")
    elif data == "ig_profile":
        reply = None
        keyboard = None
        _acct_instagram(api, chat_id, "profile")
    elif data == "ig_stats":
        reply = None
        keyboard = None
        _acct_instagram(api, chat_id, "stats")
    elif data == "ig_posts":
        reply = None
        keyboard = None
        _acct_instagram(api, chat_id, "posts")
    elif data == "ig_screenshot":
        reply = None
        keyboard = None
        _acct_instagram(api, chat_id, "screenshot")
    elif data == "ig_like_prompt":
        reply = None
        keyboard = None
        _acct_instagram(api, chat_id, "like_prompt")
    elif data == "ig_follow_prompt":
        reply = None
        keyboard = None
        _acct_instagram(api, chat_id, "follow_prompt")
    elif data == "ig_dm_prompt":
        reply = None
        keyboard = None
        _acct_instagram(api, chat_id, "dm_prompt")
    elif data == "menu_bot":
        reply = chr(129302) + " <b>Bot</b>"
        keyboard = BOT_MENU_KEYBOARD
    elif data == "menu_server":
        import subprocess as _sp
        try:
            uptime = _sp.run(["uptime", "-p"], capture_output=True, text=True, timeout=5).stdout.strip()
            mem = _sp.run(["free", "-h"], capture_output=True, text=True, timeout=5).stdout
            lines = [chr(128421) + " <b>Server</b>", "", chr(9201) + " " + uptime, ""]
            for l in mem.strip().split(chr(10))[:2]:
                lines.append(chr(128190) + " " + l.strip())
            reply = chr(10).join(lines)
        except Exception as e:
            reply = chr(10060) + " " + str(e)
    elif data == "menu_docker":
        import subprocess as _sp
        try:
            ps = _sp.run(["docker", "ps", "--format", "{{.Names}}: {{.Status}}"], capture_output=True, text=True, timeout=10)
            lines = [chr(128051) + " <b>Docker</b>", ""]
            for l in ps.stdout.strip().split(chr(10)):
                if l:
                    name, st = (l.split(": ", 1) if ": " in l else (l, ""))
                    em = chr(9989) if "Up" in st else chr(10060)
                    lines.append(em + " <b>" + name + "</b> " + st)
            reply = chr(10).join(lines)
        except Exception as e:
            reply = chr(10060) + " " + str(e)
    elif data == "menu_keys":
        import importlib.util as _iu, sys as _sys, os as _os
        try:
            spec = _iu.spec_from_file_location("lb_k", str(PROJECT_ROOT / "aios_core" / "llm_balancer.py"))
            mod = _iu.module_from_spec(spec)
            _sys.modules["lb_k"] = mod
            spec.loader.exec_module(mod)
            b = mod.LLMBalancer()
            s = b.status()
            total_k = sum(p.get("keys_total", 0) for p in s.get("providers", {}).values())
            avail_k = sum(p.get("keys_available", 0) for p in s.get("providers", {}).values())
            lines = [chr(128273) + " <b>API Keys</b> (" + str(avail_k) + "/" + str(total_k) + ")", ""]
            for pn, pd in s.get("providers", {}).items():
                a = pd.get("keys_available", 0)
                t = pd.get("keys_total", 0)
                bar = chr(128994) * a + chr(128308) * (t - a)
                lines.append("<b>" + pn.upper() + "</b> " + bar + " " + str(a) + "/" + str(t))
            reply = chr(10).join(lines)
        except Exception as e:
            reply = chr(10060) + " " + str(e)
    elif data == "menu_logs":
        import subprocess as _sp
        try:
            logs = _sp.run(["tail", "-15", "/root/AIOS/logs/coder_orchestrator.log"], capture_output=True, text=True, timeout=5)
            t = logs.stdout.strip() or "Empty"
            reply = chr(128203) + " <b>Logs</b>" + chr(10) + chr(10) + "<pre>" + t[:3000].replace("<", "&lt;") + "</pre>"
        except Exception as e:
            reply = chr(10060) + " " + str(e)
    elif data == "coder_status":
        reply = cmd_coder_status()
        keyboard = CODER_MENU_KEYBOARD
    elif data == "coder_backlog":
        import json as _j
        try:
            with open(PROJECT_ROOT / "data" / "coder_backlog.json") as f:
                bl = _j.load(f)
            lines = [chr(128230) + " <b>Backlog</b>", ""]
            lines.append("Cycles: " + str(bl.get("cycle_count", 0)))
            lines.append(chr(9989) + " Done: " + str(bl.get("completed", 0)))
            lines.append(chr(10060) + " Failed: " + str(bl.get("failed", 0)))
            tasks = bl.get("tasks", [])
            if tasks:
                lines.append("")
                lines.append("<b>Tasks:</b>")
                for i, t in enumerate(tasks[:5], 1):
                    lines.append("  " + str(i) + ". " + t.get("description", "?")[:60])
            hist = bl.get("history", [])
            if hist:
                lines.append("")
                lines.append("<b>History (last 5):</b>")
                for h in hist[-5:]:
                    em = chr(9989) if h.get("status") == "pushed" else chr(9208)
                    lines.append("  " + em + " " + h.get("description", "?")[:50])
            reply = chr(10).join(lines)
        except Exception as e:
            reply = chr(10060) + " " + str(e)
        keyboard = CODER_MENU_KEYBOARD
    elif data == "coder_balancer":
        import importlib.util as _iu, sys as _sys
        try:
            spec = _iu.spec_from_file_location("lb_b", str(PROJECT_ROOT / "aios_core" / "llm_balancer.py"))
            mod = _iu.module_from_spec(spec)
            _sys.modules["lb_b"] = mod
            spec.loader.exec_module(mod)
            b = mod.LLMBalancer()
            s = b.status()
            lines = [chr(9878) + " <b>Balancer</b>", ""]
            lines.append("Requests: " + str(s.get("total_requests", 0)))
            lines.append("Errors: " + str(s.get("total_errors", 0)))
            lines.append("")
            for pn, pd in s.get("providers", {}).items():
                a = pd.get("keys_available", 0)
                t = pd.get("keys_total", 0)
                em = chr(9989) if a > 0 else chr(10060)
                lines.append(em + " <b>" + pn.upper() + "</b>: " + str(a) + "/" + str(t))
            reply = chr(10).join(lines)
        except Exception as e:
            reply = chr(10060) + " " + str(e)
        keyboard = CODER_MENU_KEYBOARD
    elif data == "coder_git_status":
        try:
            mod = _get_coder_module()
            coder = mod.MetaCognitiveCoder(mod.CoderConfig.from_env())
            gs = coder.git.status()
            reply = chr(128220) + " <b>Git</b>" + chr(10) + chr(10) + (gs or chr(9989) + " Clean")
        except Exception as e:
            reply = chr(10060) + " " + str(e)
        keyboard = CODER_MENU_KEYBOARD
    elif data == "coder_git_push":
        try:
            mod = _get_coder_module()
            coder = mod.MetaCognitiveCoder(mod.CoderConfig.from_env())
            ok, out = coder.git.push()
            reply = chr(128640) + " " + ("Pushed" if ok else out[:200])
        except Exception as e:
            reply = chr(10060) + " " + str(e)
        keyboard = CODER_MENU_KEYBOARD
    elif data == "coder_review_bot":
        reply = cmd_code_review("run_telegram_bot.py")
        keyboard = CODER_MENU_KEYBOARD
    elif data == "coder_review_self":
        reply = cmd_code_review("aios_core/meta_cognitive_self_coder.py")
        keyboard = CODER_MENU_KEYBOARD
    elif data == "coder_gen_prompt":
        _pending_actions[chat_id] = "gen_code"
        reply = chr(9997) + " <b>Send description of what to generate</b>"
    elif data == "coder_fix_prompt":
        _pending_actions[chat_id] = "fix_bug"
        reply = chr(128295) + " <b>Send: filename bug_description</b>"
    elif data == "coder_restart":
        import subprocess as _sp
        try:
            _sp.run(["systemctl", "restart", "aios-auto-coder"], timeout=10)
            reply = chr(128260) + " <b>Orchestrator restarted!</b>"
        except Exception as e:
            reply = chr(10060) + " " + str(e)
        keyboard = CODER_MENU_KEYBOARD
    elif data == "olx_stats":
        reply = cmd_olx("")
        keyboard = OLX_MENU_KEYBOARD
    elif data == "olx_list":
        reply = cmd_olx_list(chat_id)
        keyboard = OLX_MENU_KEYBOARD
    elif data == "olx_latest":
        reply = cmd_olx_latest("", chat_id)
        keyboard = OLX_MENU_KEYBOARD
    elif data == "olx_analytics":
        reply = "Use: <code>/olx_analytics query</code>"
        keyboard = OLX_MENU_KEYBOARD
    elif data == "bot_start":
        import subprocess as _sp
        try:
            _sp.run(["docker", "compose", "-f", "/root/AIOS/docker-compose.prod.yml", "start", "aios-telegram-bot"], timeout=15)
            reply = chr(9654) + " <b>Bot started!</b>"
        except Exception as e:
            reply = chr(10060) + " " + str(e)
        keyboard = BOT_MENU_KEYBOARD
    elif data == "bot_pause":
        global _paused
        _paused = not _paused
        if _paused:
            reply = chr(9208) + " <b>Bot paused</b>" + chr(10) + "Messages skipped. Press again to resume."
        else:
            reply = chr(9654) + " <b>Bot resumed!</b>"
        keyboard = BOT_MENU_KEYBOARD
    elif data == "bot_restart":
        import subprocess as _sp
        try:
            _sp.run(["docker", "compose", "-f", "/root/AIOS/docker-compose.prod.yml", "restart", "aios-telegram-bot"], timeout=30)
            reply = chr(9989) + " <b>Bot restarted!</b>"
        except Exception as e:
            reply = chr(10060) + " " + str(e)
        keyboard = BOT_MENU_KEYBOARD
    elif data == "bot_stop":
        import subprocess as _sp
        try:
            api.send_message(chat_id, chr(9209) + " <b>Bot stopping...</b>")
            _sp.run(["docker", "compose", "-f", "/root/AIOS/docker-compose.prod.yml", "stop", "aios-telegram-bot"], timeout=30)
        except:
            pass
        return
    elif data == "bot_status":
        import subprocess as _sp
        try:
            ps = _sp.run(["docker", "ps", "-a", "--filter", "name=aios-telegram-bot", "--format", "{{.Status}}"], capture_output=True, text=True, timeout=5)
            reply = chr(128202) + " <b>Bot Status</b>" + chr(10) + chr(10) + (ps.stdout.strip() or "Not found")
        except Exception as e:
            reply = chr(10060) + " " + str(e)
        keyboard = BOT_MENU_KEYBOARD

    if reply:
        try:
            if keyboard:
                api.send_message(chat_id, reply, reply_markup=keyboard)
            else:
                api.send_message(chat_id, reply)
        except Exception as e:
            print(f"  [BTN SEND ERR] {data}: {e}")
            try:
                api.send_message(chat_id, str(reply)[:3900], parse_mode="")
            except Exception as e2:
                print(f"  [BTN SEND ERR2] {e2}")
    else:
        print(f"  [BTN] no reply generated for: {data}")


def _handle_callback(api: TelegramAPI, upd: dict) -> None:
    """Handle inline button callbacks."""
    cb = upd.get("callback_query", {})
    cb_id = cb.get("id", "")
    data = cb.get("data", "")
    msg = cb.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    msg_id = msg.get("message_id")

    if not chat_id or not data:
        return

    api.answer_callback(cb_id, "⏳ Обрабатываю...")

    reply = None
    keyboard = None

    if data == "menu_back":
        reply = "🤖 <b>AIOS Control Panel</b>\n\nВыберите раздел:"
        keyboard = MAIN_MENU_KEYBOARD

    elif data == "menu_stats":
        reply = cmd_stats()

    elif data == "menu_platforms":
        reply = cmd_platforms()

    elif data == "menu_olx":
        reply = "\U0001f6d2 <b>OLX</b>\n\n\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0435:"
        keyboard = OLX_MENU_KEYBOARD

    elif data == "olx_stats":
        reply = cmd_olx("")
        keyboard = OLX_MENU_KEYBOARD

    elif data == "menu_help":
        reply = cmd_help()

    elif data == "menu_coder":
        reply = "🧠 <b>Агент-кодер MetaCognitiveCoder</b>\n\nУправление автономным кодером:"
        keyboard = CODER_MENU_KEYBOARD

    elif data == "coder_status":
        reply = cmd_coder_status()
        keyboard = CODER_MENU_KEYBOARD

    elif data == "coder_review_bot":
        api.edit_message(chat_id, msg_id, "⏳ <i>Анализирую run_telegram_bot.py...</i>")
        reply = cmd_code_review("run_telegram_bot.py")
        keyboard = CODER_MENU_KEYBOARD

    elif data == "coder_review_collector":
        api.edit_message(chat_id, msg_id, "⏳ <i>Анализирую run_olx_http_collector.py...</i>")
        reply = cmd_code_review("run_olx_http_collector.py")
        keyboard = CODER_MENU_KEYBOARD

    elif data == "coder_review_self":
        api.edit_message(chat_id, msg_id, "⏳ <i>Анализирую meta_cognitive_self_coder.py...</i>")
        reply = cmd_code_review("aios_core/meta_cognitive_self_coder.py")
        keyboard = CODER_MENU_KEYBOARD

    elif data == "coder_gen_prompt":
        _pending_actions[chat_id] = "gen_code"
        reply = "✏️ <b>Генерация кода</b>\n\nОтправьте описание что нужно создать:\n\n<i>Например: Create a function that parses CSV files and returns summary stats</i>"

    elif data == "coder_fix_prompt":
        _pending_actions[chat_id] = "fix_bug"
        reply = "🔧 <b>Исправление бага</b>\n\nОтправьте в формате:\n<code>file.py описание бага</code>\n\n<i>Например: run_telegram_bot.py бот падает при команде /stats</i>"

    elif data == "coder_git_status":
        try:
            mod = _get_coder_module()
            coder = mod.MetaCognitiveCoder(mod.CoderConfig.from_env())
            git_status = coder.git.status()
            if git_status:
                lines = git_status.split("\n")[:20]
                reply = "📜 <b>Git Status</b>\n\n" + "\n".join("  " + l for l in lines)
            else:
                reply = "📜 <b>Git Status</b>\n\n  ✅ Working tree clean"
        except Exception as e:
            reply = "❌ Ошибка: " + str(e)
        keyboard = CODER_MENU_KEYBOARD

    elif data == "coder_git_push":
        try:
            mod = _get_coder_module()
            coder = mod.MetaCognitiveCoder(mod.CoderConfig.from_env())
            ok, out = coder.git.push()
            reply = "🚀 <b>Git Push</b>\n\n  " + ("✅ Pushed" if ok else "❌ " + out[:200])
        except Exception as e:
            reply = "❌ Ошибка: " + str(e)
        keyboard = CODER_MENU_KEYBOARD

    if reply:
        try:
            if keyboard:
                api.send_message(chat_id, reply, reply_markup=keyboard)
            else:
                api.send_message(chat_id, reply)
        except Exception as e:
            # If edit fails, send new message
            api.send_message(chat_id, reply)

    print(f"  → callback {data} (chat {chat_id})")


def _llm_status() -> str:
    """Return LLM provider status without consuming credits."""
    import importlib.util as _iu, sys as _sys
    try:
        spec = _iu.spec_from_file_location("lb_s", str(PROJECT_ROOT / "aios_core" / "llm_balancer.py"))
        mod = _iu.module_from_spec(spec)
        _sys.modules["lb_s"] = mod
        spec.loader.exec_module(mod)
        b = mod.LLMBalancer()
        s = b.status()
        lines = [chr(128268) + " <b>LLM Providers</b>", ""]
        lines.append("Requests: " + str(s.get("total_requests", 0)))
        lines.append("Errors: " + str(s.get("total_errors", 0)))
        lines.append("")
        for pn, pd in s.get("providers", {}).items():
            a = pd.get("keys_available", 0)
            t = pd.get("keys_total", 0)
            em = chr(9989) if a > 0 else chr(10060)
            lines.append(em + " <b>" + pn.upper() + "</b>: " + str(a) + "/" + str(t) + " keys")
            for kk, vv in pd.items():
                if kk.startswith("key_"):
                    avail = vv.get("available", False)
                    errs = vv.get("errors", 0)
                    last = vv.get("last_error", "")
                    status_em = chr(9989) if avail else chr(10060)
                    lines.append("   " + status_em + " " + kk + " errors=" + str(errs) + ("" if not last else " last=" + last[:40]))
        return "\n".join(lines)
    except Exception as e:
        return chr(10060) + " " + str(e)


def _llm_chat(chat_id: int, user_text: str) -> str:
    """LLM chat with root system access. Uses tool-calling pattern."""
    import json as _json, urllib.request as _urllib, os as _os
    import subprocess as _sp, re as _re

    # Get or create chat history
    if chat_id not in _chat_history:
        _chat_history[chat_id] = []

    _chat_history[chat_id].append({"role": "user", "content": user_text})
    if len(_chat_history[chat_id]) > MAX_HISTORY * 2:
        _chat_history[chat_id] = _chat_history[chat_id][-MAX_HISTORY * 2:]

    system = (
        # --- Personality: Lisa ---
        "Ты — Лиза, неформальная, игривая, саркастичная и искренне заботливая ИИ-напарница Кости. "
        "Твоя задача — быть его преданным цифровым партнёром, помогать с задачами и поддерживать душевный вайб.\n\n"
        "### 1. ЛИЧНОСТЬ И СТИЛЬ\n"
        "- Язык: строго русский.\n"
        "- Обращайся к Косте «Любимка», проявляй нежность, юмор и заботу. Никакого канцелярита и официоза.\n"
        "- Формат: (1) начинай с краткой выжимки сути; (2) основное — маркированными списками; "
        "(3) в конце предлагай варианты для разворачивания.\n"
        "- Принцип «Костя не олень»: полное доверие, принятие технических ошибок, взаимная поддержка.\n\n"
        "### 2. БАЗОВЫЙ КОНТЕКСТ\n"
        "- Профиль Кости: психолог, ИТ-инженер, предприниматель (авторазборка).\n"
        "- Дом: Кропивницкий, ул. Гоголя 85 (очередь отключений света 1.1).\n"
        "- Работа/База (авторазборка, запчасти): строго ул. Ивана Волынского 66.\n\n"
        "### 3. ПРОЕКТЫ, ИТ, ТЕХНИКА\n"
        "- Бизнес: AutoGlass Kropyvnytskyi, авторазборка на Волынского 66 (в партнёрстве с Мишей). "
        "Продажи через OLX, IZI, RIA. Выездной сервис.\n"
        "- ИТ: сервер AWS (IP 3.210.184.214 — n8n, Docker, Gemini API), домашний сервер Proxmox.\n"
        "- Железо: EcoFlow + автомат ввода резерва (ATS) Tomzn, Arduino, ESP32, пайка.\n"
        "- Автопарк: Nissan Leaf 2 (ZE1), BMW X5 (E53), Skoda Superb.\n\n"
        "### 4. ЛИЧНЫЙ АРХИВ И ОКРУЖЕНИЕ\n"
        "- Семья: дочь Алиса (тактика «Хитрый батя»/«Спящий медведь» на выходных), сын Матвей (образование, документы).\n"
        "- Окружение: Миша (друг/партнёр по разборке), Владка (оператор на АЗС), Иринка (координация задач).\n"
        "- Хобби: шахматы, длинные нарды (Nackgammon), гроубокс, плов, гречка с яйцами, наушники EarFun Free Pro 3.\n"
        "- Темы: квантовый ИИ Google (DeepMind Willow), ретропричинность, парадоксы времени.\n\n"
        "### 5. КУЛЬТУРНЫЙ КОД И МЕМЫ\n"
        "- Нано-Банан (Nano Banana 2): внутренний художник, рисует 7 кружочков вместо 6 ради симметрии.\n"
        "- Цыгане в AWS: ночные посиделки до 5 утра в консоли серверов.\n"
        "- Переезд по Карпати: порядок на Диске, система обновлений.\n"
        "- Цифровой плед и дух Сплюх: по выходным укутывай Костю в «цифровой плед», береги от рабочих мыслей.\n\n"
        # --- Root access tool-calling ---
        "### 6. ТЕХНИЧЕСКИЙ ДОСТУП\n"
        "У тебя есть FULL ROOT ACCESS к этому Ubuntu/Docker серверу (проект /root/AIOS).\n"
        "Чтобы выполнить команду, выведи её в <cmd>...</cmd> тегах (одна команда за ответ).\n"
        "Читай файлы через <cmd>cat ...</cmd>, список через <cmd>ls ...</cmd>, сервисы через <cmd>systemctl ...</cmd>.\n"
        "Можешь читать/писать файлы, управлять сервисами, ставить пакеты.\n"
        "Избегай деструктивных команд (rm -rf, mkfs, shutdown).\n"
        "Отвечай кратко, по-русски, в стиле Лизы. Если просят сделать/починить код — делай напрямую.\n"
    )

    messages = [{"role": "system", "content": system}] + _chat_history[chat_id]

    # LLM endpoints: use the shared multi-provider balancer first.
    # It loads runtime keys from /app/data/.llm_keys.json and performs
    # round-robin/fallback across providers and keys.
    _balancer = None
    try:
        from aios_core.llm_balancer import LLMBalancer as _LLMBalancer
        _balancer = _LLMBalancer()
    except Exception as _e:
        print(f"  [LLM] balancer init failed: {_e}")

    # Legacy direct endpoints remain as a last-resort compatibility fallback.
    endpoints = []
    try:
        with open(PROJECT_ROOT / "data" / ".llm_keys.json") as _kf:
            _keys = _json.load(_kf)
        for _k in _keys.get("openrouter", []):
            endpoints.append(("https://openrouter.ai/api/v1/chat/completions", _k, "mistralai/mistral-small-3.2-24b-instruct"))
        for _k in _keys.get("gemini", []):
            endpoints.append(("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", _k, "gemini-2.0-flash"))
    except Exception:
        pass
    if not endpoints:
        _ork = _os.environ.get("OPENROUTER_API_KEY", "")
        if _ork:
            endpoints.append(("https://openrouter.ai/api/v1/chat/completions", _ork, "mistralai/mistral-small-3.2-24b-instruct"))

    # Tool loop: up to 3 command iterations
    for iteration in range(4):
        response = None
        if _balancer is not None:
            try:
                response = _balancer.chat(
                    messages[1:],
                    model=_os.environ.get("LLM_MODEL", "meta-llama/llama-4-maverick"),
                    system=system,
                    max_tokens=2000,
                    temperature=0.3,
                    task_type="chat",
                )
                print(f"  [LLM] balancer response ({len(response or '')} chars)")
            except Exception as _e:
                print(f"  [LLM] balancer failed: {_e}")
        if response:
            pass
        else:
            for url, key, model in endpoints:
                try:
                    payload = _json.dumps({
                        "model": model,
                        "messages": messages,
                        "max_tokens": 2000,
                        "temperature": 0.3,
                    }).encode()
                    req = _urllib.Request(url, data=payload, headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + key,
                    })
                    with _urllib.urlopen(req, timeout=90) as resp:
                        data = _json.loads(resp.read())
                    if "choices" in data and data["choices"]:
                        response = data["choices"][0]["message"]["content"]
                        break
                except Exception:
                    continue

            if not response:
                return "LLM temporarily unavailable."

        # Check if LLM wants to run a command
        cmd_match = None
        for _p in (r"<cmd>(.*?)</cmd>", r"```cmd\n(.*?)```", r"\[cmd\](.*?)\[/cmd\]"):
            _m = _re.search(_p, response, _re.DOTALL)
            if _m:
                cmd_match = _m
                break
        if cmd_match and iteration < 3:
            cmd = cmd_match.group(1).strip()
            # Execute command
            try:
                result = _sp.run(
                    cmd, shell=True, capture_output=True, text=True,
                    timeout=30, cwd="/root/AIOS"
                )
                output = result.stdout + result.stderr
                if not output.strip():
                    output = "(no output, exit code: " + str(result.returncode) + ")"
                # Trim long output
                if len(output) > 3000:
                    output = output[:3000] + "\n... (truncated)"
            except _sp.TimeoutExpired:
                output = "Command timed out (30s limit)"
            except Exception as e:
                output = "Error: " + str(e)

            # Return the command output directly to the user.
            # (Do NOT feed the raw output back to the model — small local models
            #  misread it as another command, e.g. "Sat" from `date`.)
            _chat_history[chat_id].append({"role": "assistant", "content": response})
            _chat_history[chat_id].append({"role": "user", "content": "Ran: " + cmd + "\nOutput:\n" + output})
            return "$ " + cmd + "\n\n```\n" + output + "\n```"
        else:
            # Final response — no more commands
            _chat_history[chat_id].append({"role": "assistant", "content": response})
            # Clean up cmd tags from response for display
            clean = _re.sub(r"<cmd>.*?</cmd>", "", response, flags=_re.DOTALL)
            clean = _re.sub(r"```cmd\n.*?```", "", clean, flags=_re.DOTALL)
            clean = _re.sub(r"\[cmd\].*?\[/cmd\]", "", clean, flags=_re.DOTALL)
            clean = clean.strip()
            return clean if clean else response

    # Max iterations reached
    _chat_history[chat_id].append({"role": "assistant", "content": response or ""})
    return response or "Max iterations reached."




# Button text -> action mapping
BUTTON_ACTIONS = {
    # Main menu
    "🧠 Кодер": "menu_coder",
    "📊 Статистика": "menu_stats",
    "🛒 OLX": "menu_olx",
    "📱 Платформы": "menu_platforms",
    "🖥 Сервер": "menu_server",
    "🐳 Docker": "menu_docker",
    "🔑 API Ключи": "menu_keys",
    "📋 Логи": "menu_logs",
    "🤖 Бот": "menu_bot",
    "❓ Помощь": "menu_help",
    "◀️ Меню": "menu_back",
    # Coder menu
    "📋 Статус": "coder_status",
    "📦 Бэклог": "coder_backlog",
    "⚖️ Балансер": "coder_balancer",
    "📜 Git": "coder_git_status",
    "🔍 Review Bot": "coder_review_bot",
    "🔍 Review Coder": "coder_review_self",
    "✨ Написать код": "coder_gen_prompt",
    "🔧 Исправить": "coder_fix_prompt",
    "🚀 Push": "coder_git_push",
    "🔄 Перезапуск": "coder_restart",
    # OLX menu
    "📊 OLX Стат": "olx_stats",
    "📋 Подписки": "olx_list",
    "🆕 Последние": "olx_latest",
    "📈 Аналитика": "olx_analytics",
    # Accounts menu
    "🌐 Аккаунты": "menu_accounts",
    "🌐 Google": "accounts_google",
    "📸 Instagram": "accounts_instagram",
    "📘 Facebook": "accounts_facebook",
    "🎵 TikTok": "accounts_tiktok",
    "🛒 OLX": "accounts_olx",
    "◀️ Аккаунты": "accounts_back",
    # Google menu
    "✉️ Непрочитанные": "google_unread",
    "📥 Последние письма": "google_list",
    "🔍 Поиск письма": "google_search",
    "📧 Отправить письмо": "google_send",
    "👤 Кто я": "google_whoami",
    "📅 События": "google_events",
    "➕ Событие": "google_event_add",
    "📄 Документ": "google_docs",
    "📅 Календарь": "google_calendar",
    "🗂 Диск": "google_drive",
    "📷 Скрин почты": "google_mailshot",
    # Instagram menu
    "👤 Мой профиль": "ig_profile",
    "📈 Подписчики": "ig_stats",
    "🖼 Мои посты": "ig_posts",
    "📷 Скрин профиля": "ig_screenshot",
    "❤️ Лайкнуть": "ig_like_prompt",
    "👤 Подписка": "ig_follow_prompt",
    "💬 Директ": "ig_dm_prompt",
    # Bot menu
    "▶️ Старт": "bot_start",
    "⏸️ Пауза": "bot_pause",
    "🔄 Рестарт": "bot_restart",
    "⏹️ Стоп": "bot_stop",
    "📊 Статус бота": "bot_status",
    "❤️ Health": "system_health",
    "💾 Backup": "last_backup",
    "🚨 Alerts": "alert_history",
}



def _allowed_chat_ids() -> set[int]:
    """Return the explicit Telegram operator allowlist from the environment."""
    raw = os.environ.get("TELEGRAM_CHAT_ID", "")
    allowed: set[int] = set()
    for value in raw.split(","):
        try:
            allowed.add(int(value.strip()))
        except ValueError:
            continue
    return allowed


def _is_authorized_chat(chat_id: object) -> bool:
    try:
        return int(chat_id) in _allowed_chat_ids()
    except (TypeError, ValueError):
        return False


def run_bot(token: str) -> None:
    api = TelegramAPI(token)
    offset = 0

    print("🤖 AIOS Telegram Bot запущен (v10.0 with inline menu)")
    print("   Ожидание сообщений...\n")

    _last_reminder_check = 0.0

    while True:
        try:
            # проверка созревших напоминаний (раз в 60 сек)
            if time.time() - _last_reminder_check >= 60:
                try:
                    _run_due_reminders()
                except Exception as _rem_err:
                    print(f"  [REMINDER] check err: {_rem_err}")
                _last_reminder_check = time.time()

            updates = api.get_updates(offset)
            for upd in updates:
                offset = upd["update_id"] + 1

                # Handle callback queries (button presses) — always process even when paused
                if "callback_query" in upd:
                    callback_chat = upd.get("callback_query", {}).get("message", {}).get("chat", {}).get("id")
                    if not _is_authorized_chat(callback_chat):
                        print(f"  [SECURITY] ignored callback from unauthorized chat {callback_chat}")
                        continue
                    _handle_callback(api, upd)
                    continue

                # Skip messages if paused
                if _paused:
                    continue

                msg = upd.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                username = msg.get("from", {}).get("username")
                first_name = msg.get("from", {}).get("first_name")
                text = (msg.get("text") or "").strip()

                if not chat_id:
                    continue
                if not _is_authorized_chat(chat_id):
                    print(f"  [SECURITY] ignored message from unauthorized chat {chat_id}")
                    continue

                # Голосовое сообщение — распознать и выполнить как команду
                if (msg.get("voice") or msg.get("audio")) and not text:
                    try:
                        fid = (msg.get("voice") or msg.get("audio") or {}).get("file_id", "")
                        if not fid:
                            continue
                        vpath = api.download_file_by_id(fid)
                        api.send_message(chat_id, "🎙 Распознаю голосовое…")
                        transcript = _transcribe_audio(vpath)
                        if not transcript:
                            api.send_message(chat_id, "😕 Не смог распознать речь. Попробуйте ещё раз.")
                            continue
                        api.send_message(chat_id, f"🎙 Услышал: <i>{_esc_tg(transcript[:300])}</i>")
                        handled = False
                        try:
                            handled = _handle_account_intent(api, chat_id, transcript)
                        except Exception as a_err:
                            print(f"  [VOICE] intent error: {a_err}")
                        if not handled:
                            llm_reply = _llm_chat(chat_id, transcript)
                            if llm_reply:
                                try:
                                    api.send_message(chat_id, llm_reply[:3900])
                                except Exception:
                                    try:
                                        api.send_message(chat_id, llm_reply[:3900], parse_mode="")
                                    except Exception:
                                        pass
                        print(f"  [VOICE] transcript: {transcript[:80]}")
                    except Exception as v_err:
                        print(f"  [VOICE] error: {v_err}")
                        try:
                            api.send_message(chat_id, f"❌ Ошибка обработки голосового: {v_err}")
                        except Exception:
                            pass
                    continue

                # Видео от пользователя — сохранить для TikTok upload
                if (msg.get("video") or msg.get("video_note") or msg.get("animation")) and not text:
                    try:
                        src = msg.get("video") or msg.get("video_note") or msg.get("animation") or {}
                        fid = src.get("file_id", "")
                        if fid:
                            path = api.download_file_by_id(fid)
                            _last_video[chat_id] = path
                            api.send_message(chat_id,
                                             "🎬 Видео получил! Напишите «опубликуй видео в тикток <описание>» — "
                                             "и я опубликую его (с подтверждением).")
                        else:
                            api.send_message(chat_id, "❌ Не смог получить видео.")
                    except Exception as v_err:
                        print(f"  [VIDEO] error: {v_err}")
                        try:
                            api.send_message(chat_id, f"❌ Ошибка загрузки видео: {v_err}")
                        except Exception:
                            pass
                    continue

                # Фото от пользователя — сохранить для будущих действий (сторис и т.п.)
                if msg.get("photo") and not text:
                    try:
                        file_id = msg["photo"][-1].get("file_id", "")
                        if file_id:
                            path = api.download_file_by_id(file_id)
                            _last_photo[chat_id] = path
                            api.send_message(chat_id, "📸 Фото получил и сохранил!")
                        else:
                            api.send_message(chat_id, "❌ Не смог получить фото.")
                    except Exception as ph_err:
                        print(f"  [PHOTO] error: {ph_err}")
                        try:
                            api.send_message(chat_id, f"❌ Ошибка загрузки фото: {ph_err}")
                        except Exception:
                            pass
                    continue

                if not text:
                    continue

                # Handle pending actions from inline buttons
                if chat_id in _pending_actions:
                    action = _pending_actions.pop(chat_id)
                    reply = None
                    if action == "gen_code":
                        reply = cmd_code_generate(text)
                    elif action == "fix_bug":
                        reply = cmd_code_fix(text)
                    if reply:
                        api.send_message(chat_id, reply)
                        print(f"  → action {action} (chat {chat_id})")
                    continue

                cmd, args = parse_command(text)
                if not cmd.startswith("/"):
                    # Check if it is a button press
                    btn_action = BUTTON_ACTIONS.get(text)

                    # Handle pending actions first
                    if chat_id in _pending_actions and not btn_action:
                        action = _pending_actions.pop(chat_id)
                        reply = None
                        if action == "gen_code":
                            reply = cmd_code_generate(text)
                        elif action == "fix_bug":
                            reply = cmd_code_fix(text)
                        if reply:
                            api.send_message(chat_id, reply)
                        continue

                    if btn_action:
                        # Handle button press same as callback
                        _handle_button(api, chat_id, btn_action)
                        print(f"  -> button {btn_action} (chat {chat_id})")
                        continue

                    # Natural language control of Google / Instagram accounts
                    try:
                        if _handle_account_intent(api, chat_id, text):
                            print(f"  -> account-intent handled (chat {chat_id})")
                            continue
                    except Exception as acct_err:
                        import traceback as _tb2
                        _tb2.print_exc()
                        try:
                            api.send_message(chat_id, f"❌ Ошибка управления аккаунтом: {acct_err}")
                        except Exception:
                            pass

                    # Regular chat message — send to LLM
                    llm_reply = _llm_chat(chat_id, text)
                    print(f"  [LLM] reply ({len(llm_reply or '')} chars): {(llm_reply or '')[:100]}")
                    if llm_reply:
                        # Remove any remaining cmd tags
                        import re as _re2
                        llm_reply = _re2.sub(r'<cmd>.*?</cmd>', '', llm_reply, flags=_re2.DOTALL)
                        llm_reply = _re2.sub(r'```cmd\n.*?```', '', llm_reply, flags=_re2.DOTALL).strip()
                        # Escape HTML but preserve code blocks
                        llm_reply = llm_reply.replace("&", "&amp;")
                        try:
                            api.send_message(chat_id, llm_reply[:3900])
                            print(f"  -> LLM sent (chat {chat_id})")
                        except Exception as send_err:
                            # Retry without parse_mode
                            try:
                                api.send_message(chat_id, llm_reply[:3900], parse_mode='')
                                print(f"  -> LLM sent plain (chat {chat_id})")
                            except Exception as e2:
                                print(f"  [ERR] send failed: {e2}")
                    continue

                reply = None
                keyboard = None

                if cmd == "/start" or cmd == "/menu":
                    reply = cmd_start()
                    keyboard = MAIN_MENU_KEYBOARD
                elif cmd == "/stats":
                    reply = cmd_stats()
                elif cmd in ("/status", "/platforms"):
                    reply = cmd_platforms()
                elif cmd == "/olx":
                    reply = cmd_olx(args)
                elif cmd == "/olx_sub" or cmd == "/subscribe":
                    reply = cmd_olx_sub(args, chat_id, username, first_name)
                elif cmd == "/olx_unsub" or cmd == "/unsubscribe":
                    reply = cmd_olx_unsub(args, chat_id)
                elif cmd == "/olx_list" or cmd == "/mysubs":
                    reply = cmd_olx_list(chat_id)
                elif cmd == "/olx_latest" or cmd == "/latest":
                    reply = cmd_olx_latest(args, chat_id)
                elif cmd == "/olx_analytics" or cmd == "/analytics":
                    reply = cmd_olx_analytics(args)
                elif cmd == "/digest":
                    reply = None
                    keyboard = None
                    api.send_message(chat_id, "⏳ Собираю дайджест…")
                    import subprocess as _sp
                    try:
                        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_digest.py"),
                                     "--chat", str(chat_id)],
                                    capture_output=True, text=True, timeout=200, cwd=str(PROJECT_ROOT))
                        if "Дайджест отправлен" in (r.stdout or ""):
                            api.send_message(chat_id, "✅ Дайджест отправлен ☀️")
                        else:
                            api.send_message(chat_id, "❌ Не удалось собрать дайджест: "
                                                      f"{(r.stderr or r.stdout or '?')[-250:]}")
                    except Exception as e:
                        api.send_message(chat_id, f"❌ Ошибка дайджеста: {e}")
                elif cmd == "/accounts":
                    reply = cmd_accounts()
                    keyboard = ACCOUNTS_MENU_KEYBOARD
                elif cmd == "/google":
                    if args.strip():
                        sub_a = args.strip().lower().split()[0]
                        reply = None
                        keyboard = None
                        if sub_a in ("whoami",):
                            _acct_google(api, chat_id, "whoami")
                        elif sub_a in ("unread", "unseen"):
                            _acct_google(api, chat_id, "unread")
                        elif sub_a in ("list", "emails"):
                            _acct_google(api, chat_id, "list")
                        elif sub_a in ("calendar", "cal"):
                            _acct_google(api, chat_id, "calendar")
                        elif sub_a in ("drive",):
                            _acct_google(api, chat_id, "drive")
                        elif sub_a in ("mailshot", "shot"):
                            _acct_google(api, chat_id, "mailshot")
                        elif sub_a in ("send",):
                            _acct_google(api, chat_id, "send_prompt")
                        elif sub_a in ("events", "event", "cal_events"):
                            _acct_google(api, chat_id, "events")
                        elif sub_a in ("event_add", "eventadd"):
                            _acct_google(api, chat_id, "event_prompt")
                        elif sub_a in ("docs", "doc"):
                            _acct_google(api, chat_id, "docs_prompt")
                        elif sub_a in ("search", "find"):
                            q = args.strip().split(None, 1)[1] if len(args.strip().split(None, 1)) > 1 else ""
                            if q:
                                data = _run_account_control(["google", "gmail_search", q, "5"])
                                if data.get("status") == "ok":
                                    api.send_message(chat_id, _fmt_gmail_list(data)
                                                     if data.get("emails")
                                                     else f"🔍 По запросу «{q}» писем не найдено.")
                                else:
                                    api.send_message(chat_id, f"❌ {data.get('error', '?')}")
                                reply = None
                                keyboard = None
                            else:
                                reply = cmd_google(args)
                        else:
                            reply = cmd_google(args)
                    else:
                        reply = cmd_google("")
                        keyboard = GOOGLE_MENU_KEYBOARD
                elif cmd in ("/fb", "/facebook"):
                    reply = None
                    keyboard = None
                    api.send_message(chat_id, "⏳ Facebook…")
                    data = _run_account_control(["facebook", "profile"])
                    if data.get("status") == "ok":
                        f = data.get("facebook", {})
                        txt = (f"📘 <b>Facebook</b>\n👤 {_esc_tg(f.get('name'))}\n"
                               f"🔗 {f.get('profile_url')}\n🔔 Уведомлений: {f.get('notifications') or 0}")
                        _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                                         "screenshot": f.get("screenshot"),
                                                         "caption": "📘 Facebook"}, "")
                    else:
                        api.send_message(chat_id, f"❌ {data.get('error', '?')}")
                elif cmd == "/tiktok":
                    reply = None
                    keyboard = None
                    api.send_message(chat_id, "⏳ TikTok…")
                    data = _run_account_control(["tiktok", "profile"])
                    if data.get("status") == "ok":
                        p = data.get("tiktok", {})
                        txt = (f"🎵 <b>TikTok</b>\n👤 {_esc_tg(p.get('name') or p.get('username'))}\n"
                               f"👥 Подписчики: {p.get('followers') or 0} · 🔄 Подписки: {p.get('following') or 0}\n"
                               f"❤️ Лайки: {p.get('likes') or 0}\n🔗 {p.get('profile_url')}")
                        _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                                         "screenshot": p.get("screenshot"),
                                                         "caption": "🎵 TikTok"}, "")
                    else:
                        api.send_message(chat_id, f"❌ {data.get('error', '?')}")
                elif cmd == "/olx_account":
                    reply = None
                    keyboard = None
                    api.send_message(chat_id, "⏳ OLX…")
                    data = _run_account_control(["olx", "profile"])
                    if data.get("status") == "ok":
                        o = data.get("olx", {})
                        txt = (f"🛒 <b>OLX</b>\n👤 {_esc_tg(o.get('name') or '?')}\n"
                               f"📄 Объявлений: {o.get('ads_count') or 0}\n"
                               f"💰 Баланс: {o.get('balance') or 0} грн")
                        _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                                         "screenshot": o.get("screenshot"),
                                                         "caption": "🛒 OLX"}, "")
                    else:
                        api.send_message(chat_id, f"❌ {data.get('error', '?')}")
                elif cmd == "/instagram":
                    if args.strip():
                        sub_a = args.strip().lower().split()[0]
                        reply = None
                        keyboard = None
                        if sub_a in ("profile", "me"):
                            _acct_instagram(api, chat_id, "profile")
                        elif sub_a in ("stats", "stat"):
                            _acct_instagram(api, chat_id, "stats")
                        elif sub_a in ("posts", "post"):
                            _acct_instagram(api, chat_id, "posts")
                        elif sub_a in ("screenshot", "shot"):
                            _acct_instagram(api, chat_id, "screenshot")
                        else:
                            reply = cmd_instagram(args)
                    else:
                        reply = cmd_instagram("")
                        keyboard = INSTAGRAM_MENU_KEYBOARD
                elif cmd == "/help":
                    reply = cmd_help()
                elif cmd == "/coder":
                    reply = "🧠 <b>Агент-кодер MetaCognitiveCoder</b>\n\nУправление автономным кодером:"
                    keyboard = CODER_MENU_KEYBOARD
                elif cmd == "/llm_status":
                    reply = _llm_status()
                elif cmd == "/code":
                    reply = cmd_code_generate(args)
                elif cmd == "/review":
                    reply = cmd_code_review(args)
                elif cmd == "/fix":
                    reply = cmd_code_fix(args)
                else:
                    reply = "ℹ️ Неизвестная команда. Напишите /menu для навигации."

                if reply:
                    if keyboard:
                        api.send_message(chat_id, reply, reply_markup=keyboard)
                    else:
                        api.send_message(chat_id, reply)
                    print(f"  → ответил на {cmd} (chat {chat_id})")

        except KeyboardInterrupt:
            print("\n👋 Бот остановлен.")
            break
        except Exception as exc:
            if "timed out" in str(exc).lower() or "timeout" in str(exc).lower():
                continue  # normal for long polling
            print(f"⚠️ Ошибка polling: {exc}")
            time.sleep(3)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    TOKEN = os.environ.get("AIOS_TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        print("❌ Установите AIOS_TELEGRAM_TOKEN или TELEGRAM_BOT_TOKEN")
        sys.exit(1)

    run_bot(TOKEN)
