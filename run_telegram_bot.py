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


def _smart_model() -> str:
    """Умная модель для чата владельца с авто-переключением по нагрузке.

    Пока клиентов/сессий мало — gemini-2.5-pro (максимальное качество);
    при большом потоке — gemini-2.5-flash (дешевле). Явный выбор через
    AIOS_PLANNER_MODEL переопределяет всё.
    """
    override = os.environ.get("AIOS_PLANNER_MODEL", "").strip()
    if override:
        return override
    threshold = int(os.environ.get("AIOS_SMART_MODEL_THRESHOLD", "10") or 10)
    try:
        _sdir = PROJECT_ROOT / "data" / "autonomy_sessions"
        active = len(list(_sdir.glob("*.json"))) if _sdir.exists() else 0
    except Exception:
        active = 0
    return "gemini-2.5-flash" if active >= threshold else "gemini-2.5-pro"

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
        try:
            return self._request("sendMessage", payload)
        except urllib.error.HTTPError as e:
            # Telegram 400 Bad Request: невалидный HTML (raw <...>) — повторяем как plain text
            if e.code == 400 and parse_mode == "HTML":
                payload["parse_mode"] = ""
                return self._request("sendMessage", payload)
            raise

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
        try:
            return self._request("editMessageText", payload)
        except urllib.error.HTTPError as e:
            if e.code == 400 and parse_mode == "HTML":
                payload["parse_mode"] = ""
                return self._request("editMessageText", payload)
            raise

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

    def send_voice(self, chat_id: int, voice_path: str, caption: str = "") -> dict:
        return self._multipart("sendVoice", chat_id, "voice", voice_path, caption)


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
# Ждём описание детали после фото: chat_id -> True
_photo_pending: dict[int, bool] = {}
# Последнее сгенерированное объявление OLX: chat_id -> part
_last_gen_ad: dict[int, str] = {}
# Последнее видео, присланное пользователем (для TikTok upload): chat_id -> путь
_last_video: dict[int, str] = {}
# Последние id писем, показанных в чате: chat_id -> [ids...]
_last_gmail_ids: dict[int, list[str]] = {}
# Ожидающие подтверждения действий: chat_id -> {"kind": ..., "data": ...}
_pending_confirm: dict[int, dict] = {}
# Короткоживущая навигация по уже подтверждённым черновикам маршрутов.
_phone_route_drafts: dict[int, dict] = {}


def _run_account_control(args: list[str], timeout: int = 160) -> dict:
    """Запустить run_account_control.py (хелпер управления аккаунтами)."""
    import subprocess as _sp
    py = "/opt/aios/.venv/bin/python"
    helper = str(PROJECT_ROOT / "run_account_control.py")
    # IMAP/SMTP-команды не требуют X; браузерные — требуют xvfb
    # viber — нативный десктоп на постоянном дисплее :1 (без xvfb)
    if args and args[0] in ("viber", "signal"):
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
                         "Напишите «найди письмо &lt;запрос&gt;», например «найди письмо от github»")
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
                               model=_smart_model(),
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


# --------------------------------------------------------------- Голосовые ответы
VOICE_REPLY_FILE = PROJECT_ROOT / "data" / "voice_reply.json"


def _voice_enabled(chat_id: int) -> bool:
    try:
        return bool(json.loads(VOICE_REPLY_FILE.read_text(encoding="utf-8")).get(str(chat_id), False))
    except Exception:
        return False


def _set_voice_enabled(chat_id: int, on: bool) -> None:
    try:
        cfg = json.loads(VOICE_REPLY_FILE.read_text(encoding="utf-8"))
    except Exception:
        cfg = {}
    cfg[str(chat_id)] = on
    VOICE_REPLY_FILE.parent.mkdir(parents=True, exist_ok=True)
    VOICE_REPLY_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def _send_voice_reply(api, chat_id: int, text: str) -> bool:
    """Озвучить текст через gTTS и отправить голосовое."""
    try:
        from gtts import gTTS
    except ImportError:
        return False
    clean = text.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "")
    clean = clean.replace("&amp;", "и").replace("&lt;", "<").replace("&gt;", ">")[:1500]
    try:
        tts = gTTS(text=clean, lang="ru")
        path = f"/tmp/aios_voice_reply_{int(time.time() * 1000)}.mp3"
        tts.save(path)
        api.send_voice(chat_id, path)
        return True
    except Exception as e:
        print(f"  [VOICE-REPLY] err: {e}")
        return False


# --------------------------------------------------------------- Шаблоны
TEMPLATES_FILE = PROJECT_ROOT / "data" / "templates.json"


def _load_templates() -> dict:
    try:
        return json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_templates(tpl: dict) -> None:
    TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATES_FILE.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")


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
    """«напомни [завтра/сегодня/в] <HH:MM> <текст>» + повторяющиеся («каждый день/неделю/месяц»)."""
    import re as _re
    text_clean = _re.sub(r"^(напомни|напоминание|remind)\s*:?\s*", "", text, flags=_re.IGNORECASE).strip()

    # повторяющиеся: «напоминай каждый день в 09:00 ...»
    m_repeat = _re.search(r"(каждый|каждую|раз в)\s+(день|неделю|месяц|утро|вечер)", text_clean.lower())
    if m_repeat:
        period = m_repeat.group(2)
        m_time = _re.search(r"\b(\d{1,2})[:.](\d{2})\b", text_clean)
        if m_time:
            hh, mm = int(m_time.group(1)), int(m_time.group(2))
            body = _re.sub(r"^(напоминай|напомни)\s*(каждый|каждую|раз в)\s*(день|неделю|месяц|утро|вечер)\s*", "", text_clean, flags=_re.IGNORECASE)
            body = _re.sub(r"\b\d{1,2}[:.]\d{2}\b", "", body).strip()
            if "утро" in period:
                hh, mm = 9, 0
            elif "вечер" in period:
                hh, mm = 21, 0
            reminders = _load_reminders()
            reminders.append({
                "chat_id": chat_id,
                "at": datetime.now().replace(hour=hh, minute=mm, second=0, microsecond=0).isoformat(),
                "text": body or "(напоминание)",
                "repeat": period,  # день|неделю|месяц
            })
            _save_reminders(reminders)
            api.send_message(chat_id, f"🔁 Напоминаю {period} в {hh:02d}:{mm:02d}: «{body[:100]}»")
            return
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
            continue
        # повторяющиеся: переносим на следующий период
        repeat = r.get("repeat")
        if repeat:
            base = datetime.fromisoformat(r["at"])
            if repeat == "день":
                nxt = base + timedelta(days=1)
            elif repeat == "неделю":
                nxt = base + timedelta(weeks=1)
            else:  # месяц
                try:
                    nxt = base.replace(month=base.month + 1)
                except ValueError:
                    nxt = base.replace(year=base.year + 1, month=base.month % 12 + 1)
            left.append({**r, "at": nxt.isoformat()})
    _save_reminders(left)
    return len(due)


# ---------------------------------------------------------------------------
# Единый инбокс — продвинутая версия
# ---------------------------------------------------------------------------

# Последний собранный инбокс по чатам: chat_id -> [items]
_last_inbox: dict[int, list[dict]] = {}
_last_inbox_filters: dict[int, dict] = {}
INBOX_SCHEDULE_FILE = PROJECT_ROOT / "data" / "inbox_schedule.json"

# Каналы и их эмодзи
_CHANNELS = {
    "gmail": ("✉️", "Почта"),
    "tg": ("✈️", "Telegram"),
    "ig": ("📸", "Instagram DM"),
    "messenger": ("💬", "Messenger"),
    "viber": ("💜", "Viber"),
    "signal": ("🔒", "Signal"),
    "android": ("📲", "Телефон"),
    "olx": ("🛒", "OLX"),
}


def _is_service_preview(text: str) -> bool:
    """Служебные события не должны выглядеть как новые клиентские сообщения."""
    low = " ".join(str(text or "").casefold().split())
    return any(marker in low for marker in (
        "голосовий виклик завершився", "голосовой вызов завершился",
        "відеовиклик завершився", "видеовызов завершился", "started a call",
        "ended a call", "вызов завершен", "виклик завершено",
    ))


def _parse_inbox_filters(text: str) -> dict:
    """Парсинг фильтров инбокса: only_unread, channels."""
    t = text.lower()
    filters = {"unread_only": False, "channels": []}
    if any(w in t for w in ("только непрочитанное", "только непрочитанные", "непрочитанн")):
        filters["unread_only"] = True
    if any(w in t for w in ("только почта", "только гмаил", "только gmail")):
        filters["channels"].append("gmail")
    if any(w in t for w in ("только телеграм", "только tg", "только телега", "только личка")):
        filters["channels"].append("tg")
    if any(w in t for w in ("только инстаграм", "только инст", "только direct", "только ig")):
        filters["channels"].append("ig")
    if any(w in t for w in ("только мессенджер", "только messenger", "только фб чат")):
        filters["channels"].append("messenger")
    if any(w in t for w in ("только вайбер", "только вибер", "только viber")):
        filters["channels"].append("viber")
    if any(w in t for w in ("только signal", "только сигнал", "только сигнaл")):
        filters["channels"].append("signal")
    if any(w in t for w in ("только телефон", "только android", "только андроид")):
        filters["channels"].append("android")
    if any(w in t for w in ("только олх", "только olx")):
        filters["channels"].append("olx")
    return filters


def _collect_inbox(filters: dict | None = None) -> tuple[list[dict], str]:
    """Собрать пункты инбокса. Возвращает (items, summary)."""
    filters = filters or {}
    chans = filters.get("channels") or []
    unread_only = filters.get("unread_only", False)
    items: list[dict] = []
    summary_parts: list[str] = []

    def _want(ch: str) -> bool:
        return (not chans) or ch in chans

    # 1) почта
    if _want("gmail"):
        try:
            g = _run_account_control(["google", "gmail_list", "5"])
            if g.get("status") == "ok" and g.get("emails"):
                for e in g["emails"]:
                    if unread_only and not e.get("unread"):
                        continue
                    items.append({
                        "channel": "gmail",
                        "ref": e.get("id", ""),
                        "title": e.get("subject", "(без темы)"),
                        "preview": (e.get("from") or "") + " · " + (e.get("snippet") or "")[:80],
                        "unread": bool(e.get("unread")),
                        "date": (e.get("date") or "")[:22],
                    })
                unread_total = g.get("unread_total", 0)
                if unread_total:
                    summary_parts.append(f"✉️ {unread_total} непрочитанных писем")
        except Exception:
            pass

    # 2) Telegram
    if _want("tg"):
        try:
            tg = _run_account_control(["tg", "dialogs", "10"])
            if tg.get("status") == "ok" and tg.get("dialogs"):
                unread_d = [d for d in tg["dialogs"] if d.get("unread")]
                src = unread_d if unread_only else tg["dialogs"]
                for d in src[:6]:
                    items.append({
                        "channel": "tg",
                        "ref": d.get("name") or str(d.get("id")),
                        "title": d.get("name") or "?",
                        "preview": (d.get("last_msg") or "")[:80],
                        "unread": bool(d.get("unread")),
                        "date": "",
                    })
                if unread_d:
                    summary_parts.append(f"✈️ {len(unread_d)} чатов TG с новыми")
        except Exception:
            pass

    # 3) Instagram Direct
    if _want("ig"):
        try:
            ig = _run_account_control(["instagram", "dm_list", "6"])
            if ig.get("status") == "ok" and ig.get("threads"):
                meaningful = 0
                for d in ig["threads"][:5]:
                    preview = (d.get("preview") or "")[:80]
                    service = _is_service_preview(preview)
                    if unread_only and service:
                        continue
                    items.append({
                        "channel": "ig",
                        "ref": d.get("name") or "?",
                        "title": d.get("name") or "?",
                        "preview": preview,
                        "unread": not service,
                        "service": service,
                        "date": "",
                    })
                    meaningful += int(not service)
                if meaningful:
                    summary_parts.append(f"📸 {meaningful} новых чатов IG Direct")
        except Exception:
            pass

    # 4) Messenger
    if _want("messenger"):
        try:
            ms = _run_account_control(["facebook", "messenger_list", "--limit", "6"])
            if ms.get("status") == "ok" and ms.get("chats"):
                meaningful = 0
                for c in ms["chats"][:5]:
                    preview = (c.get("preview") or "")[:80]
                    service = _is_service_preview(preview)
                    if unread_only and service:
                        continue
                    items.append({
                        "channel": "messenger",
                        "ref": c.get("name") or "?",
                        "title": c.get("name") or "?",
                        "preview": preview,
                        "unread": not service,
                        "service": service,
                        "date": "",
                    })
                    meaningful += int(not service)
                if meaningful:
                    summary_parts.append(f"💬 {meaningful} новых чатов Messenger")
        except Exception:
            pass

    # 5) Выбранные уведомления реального Android-телефона.
    if _want("android"):
        try:
            path = PROJECT_ROOT / "data" / "android_gateway" / "notifications.json"
            phone_events = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
            for event in reversed(phone_events[-30:]):
                if unread_only and event.get("read"):
                    continue
                title = str(event.get("title") or event.get("app") or "Телефон")
                app = str(event.get("app") or "Android")
                items.append({
                    "channel": "android",
                    "ref": str(event.get("id") or ""),
                    "title": f"{app}: {title}",
                    "preview": str(event.get("text") or "")[:120],
                    "unread": not bool(event.get("read")),
                    "date": str(event.get("collected_at") or "")[:19],
                })
            unread_phone = sum(1 for event in phone_events if not event.get("read"))
            if unread_phone:
                summary_parts.append(f"📲 {unread_phone} новых уведомлений телефона")
        except Exception:
            pass

    # 6) Viber Desktop. В списке чатов Viber не отдаёт надёжный unread-флаг,
    # поэтому в режиме «только непрочитанное» не подменяем неизвестное значение.
    if _want("viber") and not unread_only:
        try:
            vb = _run_account_control(["viber", "chats"])
            if vb.get("status") == "ok" and vb.get("chats"):
                seen_viber = set()
                for c in vb["chats"][:12]:
                    name = str(c.get("name") or "").strip()
                    if not name or name.casefold() in seen_viber:
                        continue
                    seen_viber.add(name.casefold())
                    items.append({
                        "channel": "viber",
                        "ref": name,
                        "title": name,
                        "preview": "Viber: откройте пункт, чтобы прочитать последние сообщения",
                        "unread": False,
                        "date": "",
                    })
                if seen_viber:
                    summary_parts.append(f"💜 {len(seen_viber)} чатов Viber")
        except Exception:
            pass

    # 6) Signal Desktop. OCR не даёт надёжный unread-флаг, поэтому в
    # режиме «только непрочитанное» Signal не подменяет неизвестные данные.
    if _want("signal") and not unread_only:
        try:
            sig = _run_account_control(["signal", "chats"])
            if sig.get("status") == "ok" and sig.get("chats"):
                seen_signal = set()
                for c in sig["chats"][:12]:
                    name = str(c.get("name") or "").strip()
                    if not name or name.casefold() in seen_signal:
                        continue
                    seen_signal.add(name.casefold())
                    items.append({
                        "channel": "signal",
                        "ref": name,
                        "title": name,
                        "preview": "Signal: откройте пункт, чтобы прочитать последние сообщения",
                        "unread": False,
                        "date": "",
                    })
                if seen_signal:
                    summary_parts.append(f"🔒 {len(seen_signal)} чатов Signal")
        except Exception:
            pass

    # 7) OLX
    if _want("olx"):
        try:
            olx = _run_account_control(["olx", "profile"])
            if olx.get("status") == "ok" and olx.get("olx"):
                o = olx["olx"]
                items.append({
                    "channel": "olx",
                    "ref": o.get("name") or "olx",
                    "title": f"OLX: {o.get('name') or '?'}",
                    "preview": f"объявлений: {o.get('ads_count') or 0} · баланс: {o.get('balance') or 0} грн",
                    "unread": False,
                    "date": "",
                })
        except Exception:
            pass

    summary = ", ".join(summary_parts) if summary_parts else "нового нет"
    return items, summary


def _format_inbox(items: list[dict], filters: dict | None = None) -> str:
    """Красивые компактные карточки общего инбокса для Telegram."""
    from collections import Counter

    filters = filters or {}
    unread = sum(1 for item in items if item.get("unread"))
    by_channel = Counter(item.get("channel") for item in items)
    channel_summary = " · ".join(
        f"{_CHANNELS.get(channel, ('📄', channel))[0]} {count}"
        for channel, count in by_channel.items()
    )
    head = "📥 <b>ЕДИНЫЙ ИНБОКС</b>"
    if filters.get("channels"):
        labels = [_CHANNELS.get(c, ("", c))[1] for c in filters["channels"]]
        head += " · " + ", ".join(labels)
    subtitle = f"{len(items)} карточек"
    if unread:
        subtitle += f" · 🔴 {unread} новых"
    if channel_summary:
        subtitle += f"\n{channel_summary}"
    lines = [head, f"<i>{subtitle}</i>", "━━━━━━━━━━━━━━━━"]
    for index, item in enumerate(items[:12], 1):
        emoji, channel = _CHANNELS.get(item.get("channel"), ("📄", item.get("channel", "")))
        badge = "🔴 Новое" if item.get("unread") else ("⚪ Служебное" if item.get("service") else "◦ Просмотр")
        title = _esc_tg(str(item.get("title") or "Без названия"))[:64]
        preview = _esc_tg(str(item.get("preview") or ""))[:115]
        lines.append(f"╭─ <code>{index:02d}</code> {emoji} <b>{channel}</b> · {badge}")
        lines.append(f"├ <b>{title}</b>")
        if preview:
            lines.append(f"├ <i>{preview}</i>")
        date = str(item.get("date") or "").strip()
        lines.append(f"╰ {'🕐 ' + _esc_tg(date) if date else 'Нажмите кнопку, чтобы открыть'}")
    if len(items) > 12:
        lines.append(f"\n<i>Показаны первые 12 из {len(items)} карточек.</i>")
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append("<i>Откройте карточку кнопкой ниже · «ответь на N: текст» · «сводка»</i>")
    return "\n".join(lines)[:3900]


def _inbox_keyboard(items: list[dict]) -> dict | None:
    """Удобные кнопки карточек: открыть, обновить, сводка, отметить прочитанным."""
    if not items:
        return None
    rows = []
    button_row = []
    for index, item in enumerate(items[:8], 1):
        emoji, _ = _CHANNELS.get(item.get("channel"), ("📄", ""))
        label = f"{emoji} {index}"
        button_row.append({"text": label, "callback_data": f"inbox_read_{index}"})
        if len(button_row) == 4:
            rows.append(button_row)
            button_row = []
    if button_row:
        rows.append(button_row)
    rows.append([
        {"text": "🔄 Обновить", "callback_data": "inbox_refresh"},
        {"text": "🧠 Сводка", "callback_data": "inbox_summary"},
    ])
    rows.append([{"text": "✅ Отметить прочитанным", "callback_data": "inbox_readall"}])
    return {"inline_keyboard": rows}


def _inbox_summarize(items: list[dict]) -> str:
    """Умное резюме инбокса через LLM."""
    data_lines = []
    for i, it in enumerate(items, 1):
        em, ch = _CHANNELS.get(it["channel"], ("", it["channel"]))
        data_lines.append(f"{i}. [{ch}] {it['title']} — {it['preview'][:100]}")
    prompt = (
        "Ты — ассистент, помогающий с единым инбоксом сообщений. "
        "Ниже нумерованный список новых пунктов из разных каналов (почта, Telegram, Instagram DM, "
        "Messenger, Viber, Signal, OLX). Составь КРАТКОЕ резюме на русском (3-6 строк): что самое важное/срочное, "
        "кому стоит ответить, что проверить. Упомяни номера пунктов. "
        "Формат: начни с «🧠 Сводка:», потом маркированный список. Без воды.\n\n"
        + "\n".join(data_lines)
    )
    try:
        text = _llm_chat_direct(prompt)
        return text or "🧠 Сводка: нового ничего срочного."
    except Exception:
        return "🧠 Сводка: не удалось составить (LLM недоступен)."


def _llm_chat_direct(prompt: str) -> str:
    """Одиночный LLM-вызов (без истории), возвращает текст."""
    import urllib.request as _urllib
    _b = None
    try:
        from aios_core.llm_balancer import LLMBalancer as _LB
        _b = _LB()
    except Exception:
        _b = None
    if _b is not None:
        try:
            r = _b.chat([{"role": "user", "content": prompt}],
                        model=_smart_model(),
                        system="Ты краткий ассистент инбокса. Отвечай на русском.",
                        max_tokens=400, temperature=0.3, task_type="chat")
            if r:
                return r
        except Exception:
            pass
    try:
        key = os.environ.get("OPENROUTER_API_KEY", "")
        if key:
            payload = json.dumps({
                "model": "mistralai/mistral-small-3.2-24b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 400, "temperature": 0.3,
            }).encode()
            req = _urllib.Request("https://openrouter.ai/api/v1/chat/completions",
                                  data=payload, headers={
                                      "Content-Type": "application/json",
                                      "Authorization": "Bearer " + key})
            with _urllib.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception:
        pass
    return ""


def _inbox_reply(api, chat_id: int, item: dict, body: str) -> None:
    """Ответить на пункт инбокса в нужный канал."""
    ch = item.get("channel")
    ref = item.get("ref")
    if not body:
        api.send_message(chat_id, "❌ Укажите текст ответа: «ответь на N: текст»")
        return
    if ch == "gmail":
        # ответить на письмо (email id)
        if ref.isdigit():
            _pending_confirm[chat_id] = {"kind": "gmail_reply",
                                         "data": {"msg_id": ref, "idx": 1, "text": body}}
            api.send_message(chat_id, f"📧 Ответ на письмо «{_esc_tg(item.get('title'))[:50]}»:\n«{body[:150]}»\n\nОтправить? «да» / «нет»")
        else:
            api.send_message(chat_id, "❌ Не удалось определить письмо для ответа.")
    elif ch == "tg":
        _pending_confirm[chat_id] = {"kind": "tg_send", "data": {"ref": ref, "text": body}}
        api.send_message(chat_id, f"✈️ Ответ в Telegram <b>{_esc_tg(ref)}</b>:\n«{body[:150]}»\n\nОтправить? «да» / «нет»")
    elif ch == "ig":
        _pending_confirm[chat_id] = {"kind": "dm_send", "data": {"thread": ref, "text": body}}
        api.send_message(chat_id, f"📸 Ответ в Instagram Direct <b>{_esc_tg(ref)}</b>:\n«{body[:150]}»\n\nОтправить? «да» / «нет»")
    elif ch == "messenger":
        _pending_confirm[chat_id] = {"kind": "messenger_send", "data": {"chat": ref, "text": body}}
        api.send_message(chat_id, f"💬 Ответ в Messenger <b>{_esc_tg(ref)}</b>:\n«{body[:150]}»\n\nОтправить? «да» / «нет»")
    elif ch == "viber":
        _pending_confirm[chat_id] = {"kind": "viber_send", "data": {"chat": ref, "text": body}}
        api.send_message(chat_id, f"💜 Ответ в Viber <b>{_esc_tg(ref)}</b>:\n«{body[:150]}»\n\nОтправить? «да» / «нет»")
    elif ch == "signal":
        _pending_confirm[chat_id] = {"kind": "signal_send", "data": {"chat": ref, "text": body}}
        api.send_message(chat_id, f"🔒 Ответ в Signal <b>{_esc_tg(ref)}</b>:\n«{body[:150]}»\n\nОтправить? «да» / «нет»")
    else:
        api.send_message(chat_id, "❌ Для этого пункта ответ не поддерживается.")


def _inbox_voice(api, chat_id: int, items: list[dict]) -> None:
    """Озвучить инбокс через gTTS и отправить голосовое."""
    try:
        from gtts import gTTS
    except ImportError:
        api.send_message(chat_id, "🎙 Озвучка недоступна (gTTS не установлен).")
        return
    lines = ["Инбокс. "]
    for i, it in enumerate(items[:12], 1):
        lines.append(f"{i}. {it['title']}. {it['preview'][:60]}")
    text = " ".join(lines)[:1500]
    try:
        tts = gTTS(text=text, lang="ru")
        path = f"/tmp/aios_inbox_voice_{int(time.time())}.mp3"
        tts.save(path)
        api.send_voice(chat_id, path, caption="🎙 Инбокс голосом")
        print(f"  [INBOX] voice sent ({len(text)} chars)")
    except Exception as e:
        print(f"  [INBOX] voice err: {e}")
        api.send_message(chat_id, "🎙 Не удалось озвучить: " + str(e)[:150])


def _inbox_search(api, chat_id: int, q: str) -> None:
    """Поиск по всем каналам."""
    found = []
    # почта (полнотекстовый IMAP)
    try:
        g = _run_account_control(["google", "gmail_search", q, "5"])
        if g.get("status") == "ok" and g.get("emails"):
            for e in g["emails"][:5]:
                found.append(f"✉️ <b>{_esc_tg(e.get('subject', '?'))}</b>\n   {_esc_tg((e.get('from') or '')[:50])}")
    except Exception:
        pass
    # Telegram (топ диалогов)
    try:
        tg = _run_account_control(["tg", "dialogs", "8"])
        if tg.get("status") == "ok" and tg.get("dialogs"):
            for d in tg["dialogs"][:6]:
                name = d.get("name") or ""
                last = d.get("last_msg") or ""
                if q.lower() in last.lower() or q.lower() in name.lower():
                    found.append(f"✈️ <b>{_esc_tg(name)}</b>: {_esc_tg(last[:80])}")
    except Exception:
        pass
    # Instagram DM (топ чатов)
    try:
        ig = _run_account_control(["instagram", "dm_list", "6"])
        if ig.get("status") == "ok" and ig.get("threads"):
            for d in ig["threads"][:5]:
                if q.lower() in (d.get("preview") or "").lower() or q.lower() in (d.get("name") or "").lower():
                    found.append(f"📸 <b>{_esc_tg(d.get('name'))}</b>: {_esc_tg((d.get('preview') or '')[:80])}")
    except Exception:
        pass
    # Viber: поиск по видимым чатам без открытия переписки и без пометки прочитанным.
    try:
        vb = _run_account_control(["viber", "chats"])
        if vb.get("status") == "ok":
            for c in (vb.get("chats") or [])[:20]:
                name = str(c.get("name") or "")
                if q.lower() in name.lower():
                    found.append(f"💜 <b>{_esc_tg(name)}</b>: Viber чат")
    except Exception:
        pass
    # Signal: поиск по видимым чатам без открытия переписки.
    try:
        sig = _run_account_control(["signal", "chats"])
        if sig.get("status") == "ok":
            for c in (sig.get("chats") or [])[:20]:
                name = str(c.get("name") or "")
                if q.lower() in name.lower():
                    found.append(f"🔒 <b>{_esc_tg(name)}</b>: Signal чат")
    except Exception:
        pass
    if not found:
        api.send_message(chat_id, f"🔍 По запросу «{q}» ничего не найдено (или каналы недоступны).")
    else:
        api.send_message(chat_id, f"🔍 <b>Найдено по «{q}»:</b>\n\n" + "\n".join(found)[:3900])


def _inbox_mark_read(api, chat_id: int) -> None:
    """Отметить прочитанным (почта через IMAP, TG через userbot)."""
    done = []
    # почта: пометить все \Seen
    try:
        import run_account_control as _rac
        pw = _rac.app_password()
        if pw:
            import imaplib
            M = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            M.login(_rac.GOOGLE_EMAIL, pw)
            M.select("INBOX")
            typ, data = M.search(None, "UNSEEN")
            ids = data[0].split()
            if ids:
                M.store(b",".join(ids), "+FLAGS", "\\Seen")
            M.logout()
            done.append(f"✉️ почта: {len(ids)} прочитано")
    except Exception as e:
        print(f"  [INBOX] mark gmail err: {e}")
    # Telegram
    try:
        r = _run_account_control(["tg", "read", "Saved Messages", "--limit", "1"])
        if r.get("status") == "ok":
            done.append("✈️ Telegram: диалоги открыты (пометка частичная)")
    except Exception:
        pass
    # Пометить локально собранные Android-уведомления прочитанными.
    try:
        import subprocess as _sp
        result = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_android_notification_collector.py"), "mark-read"],
                         capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
        payload = json.loads((result.stdout or "{}").strip())
        if payload.get("status") == "ok":
            done.append(f"📲 Телефон: {payload.get('marked', 0)} уведомлений отмечено")
    except Exception:
        pass
    # Остальные desktop/Direct каналы намеренно не открываем пачкой: это либо
    # меняет состояние чатов, либо API не даёт безопасной bulk-операции.
    done.append("📸 Direct и 💬 Messenger: массовая пометка недоступна безопасно")
    done.append("💜 Viber: массовая отметка не выполнялась")
    done.append("🔒 Signal: массовая отметка не выполнялась")
    _last_inbox.pop(chat_id, None)
    _last_inbox_filters.pop(chat_id, None)
    api.send_message(chat_id,
                     "✅ <b>Инбокс обработан</b>\n━━━━━━━━━━━━━━━━\n" +
                     "\n".join(f"• {line}" for line in done) +
                     "\n━━━━━━━━━━━━━━━━\n<i>Откройте «инбокс» для обновлённых карточек.</i>")


def _inbox_schedule_cmd(api, chat_id: int, text: str) -> None:
    """Управление расписанием инбокса."""
    t = text.lower()
    try:
        sched = json.loads(INBOX_SCHEDULE_FILE.read_text(encoding="utf-8")) if INBOX_SCHEDULE_FILE.exists() else {}
    except Exception:
        sched = {}
    cur = sched.get(str(chat_id), [])
    if "отключ" in t or "выключ" in t or "убери" in t:
        sched[str(chat_id)] = []
        INBOX_SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
        INBOX_SCHEDULE_FILE.write_text(json.dumps(sched, ensure_ascii=False, indent=2), encoding="utf-8")
        api.send_message(chat_id, "⏰ Расписание инбокса отключено.")
        return
    m_time = re.search(r"\b(\d{1,2})[:.](\d{2})\b", t)
    if not m_time:
        api.send_message(chat_id, "⏰ Формат: «присылай инбокс в 09:00» или «присылай инбокс вечером в 21:00»")
        return
    hh, mm = int(m_time.group(1)), int(m_time.group(2))
    when = "утром" if hh < 12 else ("днём" if hh < 17 else "вечером")
    entry = {"time": f"{hh:02d}:{mm:02d}", "label": when}
    cur = [e for e in cur if e.get("time") != entry["time"]]
    cur.append(entry)
    sched[str(chat_id)] = sorted(cur, key=lambda e: e["time"])
    INBOX_SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    INBOX_SCHEDULE_FILE.write_text(json.dumps(sched, ensure_ascii=False, indent=2), encoding="utf-8")
    api.send_message(chat_id, f"⏰ Инбокс буду присылать {when} в {entry['time']}. "
                              f"«отключи инбокс» — убрать расписание.")


def _run_due_inbox(token: str) -> int:
    """Отправить инбокс по расписанию (раз в минуту)."""
    if not INBOX_SCHEDULE_FILE.exists():
        return 0
    try:
        sched = json.loads(INBOX_SCHEDULE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return 0
    now_hhmm = datetime.now().strftime("%H:%M")
    sent = 0
    for chat_s, entries in sched.items():
        for e in entries:
            if e.get("time") == now_hhmm:
                chat_id = int(chat_s)
                # не дублируем: файл last_sent
                last_file = PROJECT_ROOT / "data" / "inbox_last_sent.json"
                try:
                    last = json.loads(last_file.read_text(encoding="utf-8"))
                except Exception:
                    last = {}
                if last.get(str(chat_id)) == now_hhmm:
                    continue
                last[str(chat_id)] = now_hhmm
                last_file.write_text(json.dumps(last), encoding="utf-8")
                items, _ = _collect_inbox({})
                if items:
                    _last_inbox[chat_id] = items
                    try:
                        import urllib.request as _urllib
                        payload = json.dumps({"chat_id": chat_id,
                                              "text": _format_inbox(items),
                                              "parse_mode": "HTML"}).encode()
                        req = _urllib.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                              data=payload, headers={"Content-Type": "application/json"})
                        with _urllib.urlopen(req, timeout=90):
                            pass
                        sent += 1
                        print(f"  [INBOX-SCHED] sent to {chat_id}")
                    except Exception as ex:
                        print(f"  [INBOX-SCHED] err: {ex}")
    return sent


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


def _handle_sales_lifecycle_intent(api, chat_id: int, text: str) -> bool:
    """Детерминированно обработать статусы продаж без риска LLM-путаницы.

    Эти команды принадлежат владельцу бота. Изменение остатков разрешено
    только после явной фразы владельца («отправил…», «доставлено…») либо
    подтверждённого статуса Новой Почты в таймере.
    """
    raw = str(text or "").strip()
    normalized = " ".join(raw.casefold().split())
    if not normalized:
        return False
    try:
        from aios_core.sales_lifecycle import SalesLifecycle
        lifecycle = SalesLifecycle(PROJECT_ROOT)
    except Exception as exc:
        print(f"  [SALES] init error: {exc}")
        return False

    crm_phrases = ("crm", "сделки", "статус продаж", "воронка продаж", "продажи crm")
    if any(phrase in normalized for phrase in crm_phrases):
        # CRM-команды: экспорт и поиск клиента не требуют LLM и не раскрывают
        # полный номер телефона в Telegram.
        if "экспорт" in normalized or "export" in normalized:
            try:
                from run_crm import export_csv
                from aios_core.crm import CRMStore
                exported = export_csv(CRMStore(PROJECT_ROOT))
                api.send_document(chat_id, exported["file"], caption=f"💼 CRM экспорт · {exported['rows']} клиентов")
            except Exception as exc:
                api.send_message(chat_id, f"⚠️ Не удалось экспортировать CRM: {_esc_tg(str(exc))[:180]}")
            return True
        if "клиент" in normalized or "customers" in normalized:
            query = re.sub(r"^(?:crm\s*)?(?:клиенты|клиент|customers?)\s*:?\s*", "", raw, flags=re.IGNORECASE).strip()
            try:
                from aios_core.crm import CRMStore
                store = CRMStore(PROJECT_ROOT)
                if query:
                    customer = store.find(query)
                    customers = [customer] if customer else []
                else:
                    customers = store.snapshot(limit=12).get("customers", [])
                if not customers:
                    api.send_message(chat_id, "👥 CRM: клиентов по запросу не найдено.")
                    return True
                lines = ["👥 <b>Клиенты CRM</b>"]
                for customer in customers[:12]:
                    tags = " · ".join(customer.get("tags") or []) or "без тега"
                    lines.append(
                        f"• <b>{_esc_tg(customer.get('display_name'))}</b> {customer.get('phone_masked') or ''}\n"
                        f"  {customer.get('sales_count', 0)} сделок · {customer.get('lifetime_amount', 0):.0f} грн · {tags}\n"
                        f"  Последнее: {_esc_tg(customer.get('last_item') or '—')} · {_esc_tg(customer.get('last_status') or '—')}")
                api.send_message(chat_id, "\n".join(lines)[:3900])
            except Exception as exc:
                api.send_message(chat_id, f"⚠️ CRM временно недоступна: {_esc_tg(str(exc))[:180]}")
            return True

        crm = lifecycle.crm_snapshot()
        status_label = {
            "awaiting_shipment": "⏳ ждёт отправки", "ttn_created": "⏳ ТТН создана",
            "in_transit": "🚚 в пути", "delivered": "✅ доставлено",
            "returning": "↩️ возврат в пути", "returned": "↩️ возврат",
            "return_received": "📦 возвращено на склад",
        }
        lines = [
            "💼 <b>Продажи и CRM</b>",
            "━━━━━━━━━━━━━━━━",
            f"Активные: <b>{crm['active']}</b> · ждут отправки: <b>{crm['awaiting']}</b> · в пути: <b>{crm['in_transit']}</b>",
            f"Доставлено: <b>{crm['delivered']}</b> · возвраты: <b>{crm['returned']}</b> · открытые задачи: <b>{crm['open_tasks']}</b>",
            f"Сумма активных сделок: <b>{crm['pipeline_amount']:.0f} грн</b>",
        ]
        recent = crm.get("sales") or []
        if recent:
            lines.append("━━━━━━━━━━━━━━━━")
            lines.append("<b>Последние сделки</b>")
            for sale in recent[:8]:
                task = " · 📌 задача" if sale.get("task_open") else ""
                lines.append(
                    f"• {status_label.get(sale.get('status'), sale.get('status'))} · "
                    f"<b>{_esc_tg(sale.get('item'))[:70]}</b> · ТТН <code>{_esc_tg(sale.get('ttn') or '—')}</code> · "
                    f"{float(sale.get('amount') or 0):.0f} грн{task}")
        lines.append("━━━━━━━━━━━━━━━━")
        lines.append("<i>«задачи отправки» · «отправил &lt;ТТН&gt;» · «доставлено &lt;ТТН&gt;»</i>")
        api.send_message(chat_id, "\n".join(lines)[:3900])
        return True

    task_phrases = (
        "задачи отправки", "задачи по отправке", "что нужно отправить",
        "что отправить", "ожидает отправки", "задачи продаж",
    )
    if any(phrase in normalized for phrase in task_phrases):
        rows = lifecycle.list_open_tasks()
        if not rows:
            api.send_message(chat_id, "📋 Открытых задач по отправкам и возвратам нет.")
            return True
        lines = ["📋 <b>Задачи по продажам:</b>"]
        for row in rows[:15]:
            task, sale = row["task"], row["sale"]
            item = _esc_tg(sale.get("item") or "товар")
            ttn = _esc_tg(sale.get("ttn") or "—")
            if task.get("kind") == "return_receive":
                lines.append(f"• ↩️ Принять возврат: <b>{item}</b> · ТТН <code>{ttn}</code>")
            else:
                lines.append(f"• 📦 Отправить: <b>{item}</b> · ТТН <code>{ttn}</code>")
        lines.append("\nПосле передачи: «отправил <ТТН>». После доставки: «доставлено <ТТН>».")
        api.send_message(chat_id, "\n".join(lines)[:3900])
        return True

    def _reference(match) -> str:
        value = (match.group(1) or "").strip(" ,.:;—–-") if match.lastindex else ""
        generic = {"этот товар", "эту посылку", "этот", "эту", "товар", "посылку", "посылка",
                   "его", "ее", "цей товар", "цю посилку", "посилку"}
        return "" if value.casefold() in generic else value

    # Важно проверять приём возврата раньше «получил…», иначе фраза
    # «получил возврат» могла бы ошибочно закрыть продажу как доставленную.
    m = re.match(r"^(?:я\s+)?(?:получил(?:а)?\s+возврат|возврат\s+получил(?:а)?|"
                 r"принял(?:а)?\s+возврат|повернув(?:ла)?\s+на\s+склад)\b\s*(.*)$", raw, re.I)
    if m:
        result = lifecycle.mark_return_received(_reference(m), source="telegram")
    else:
        m = re.match(r"^(?:посылка\s+|товар\s+)?(?:вернулась|вернулся|возвращена|возвращен|"
                     r"повернулась|повернувся|повернено|возврат)\b\s*(.*)$", raw, re.I)
        if m:
            result = lifecycle.mark_returned(_reference(m), source="telegram")
        else:
            m = re.match(r"^(?:я\s+)?(?:(?:товар|посылку|посилку)\s+)?(?:уже\s+)?"
                         r"(?:отправил(?:а)?|відправив(?:ла)?|передал(?:а)?\s+(?:в|на)\s+"
                         r"(?:новую\s+почту|нову\s+пошту|нп)|сдал(?:а)?\s+(?:в|на)\s+"
                         r"(?:новую\s+почту|нову\s+пошту|нп))\b\s*(.*)$", raw, re.I)
            if m:
                result = lifecycle.mark_shipped(_reference(m), source="telegram")
            else:
                m = re.match(r"^(?:товар\s+|посылка\s+|посилка\s+)?(?:доставлен(?:а|о|ы)?|"
                             r"доставили|доставлено|клиент\s+получил|клієнт\s+отримав|"
                             r"отримано\s+(?:клієнтом|покупцем))\b\s*(.*)$", raw, re.I)
                if not m:
                    return False
                result = lifecycle.mark_delivered(_reference(m), source="telegram")

    message = str(result.get("message") or result.get("error") or "Не удалось обновить сделку.")
    # SalesLifecycle возвращает обычный текст. Экранируем название товара,
    # если пользователь когда-то добавил в него HTML-символы.
    api.send_message(chat_id, _esc_tg(message)[:3900])
    return True


def _send_unified_inbox(api, chat_id: int, text: str = "", filters: dict | None = None) -> None:
    """Собрать и красиво показать инбокс из одного места."""
    filters = dict(filters or _parse_inbox_filters(text))
    api.send_message(chat_id, "⏳ <b>Собираю единый инбокс…</b>\nПочта · TG · Direct · Телефон · Messenger · Viber · Signal · OLX")
    items, _summary = _collect_inbox(filters)
    if not items:
        api.send_message(chat_id, "📭 <b>Инбокс пуст</b>\nНовых карточек по выбранным каналам нет.")
        return
    _last_inbox[chat_id] = items
    _last_inbox_filters[chat_id] = filters
    lower = (text or "").casefold()
    if any(word in lower for word in ("сводк", "резюме", "кратко", "умн")):
        api.send_message(chat_id, "🧠 Составляю сводку по карточкам…")
        api.send_message(chat_id, _inbox_summarize(items)[:3900])
    else:
        api.send_message(chat_id, _format_inbox(items, filters), reply_markup=_inbox_keyboard(items))


def _handle_unified_inbox_intent(api, chat_id: int, text: str) -> bool:
    """Приоритетный роутер инбокса до Instagram Direct и прочих платформ."""
    t = " ".join((text or "").casefold().split())
    if not t:
        return False

    # Расписание должно перехватываться раньше общего слова «инбокс».
    if re.match(r"^(присылай|пришли|включи|отключи|выключи|убери)\s+инбокс", t) or \
       re.match(r"^(включи|отключи)\s+расписание\s+инбокса", t):
        _inbox_schedule_cmd(api, chat_id, text)
        return True

    # Пользовательский вариант «отметить все непрочитанные сообщения в инбоксе
    # прочитанными» раньше ошибочно попадал в обработчик Instagram Direct.
    mark_read = ((any(stem in t for stem in ("отмет", "пометь", "отмеч")) and "прочитан" in t
                  and any(word in t for word in ("инбокс", "сообщен", "все", "всё")))
                 or "всё прочитано" in t or "все прочитаны" in t)
    if mark_read:
        _inbox_mark_read(api, chat_id)
        return True

    m_reply = re.match(r"^(ответь|reply|отв[её]ть)\s+(?:на\s+)?#?(\d+)\s*:?\s*(.+)$", text, re.IGNORECASE)
    if m_reply:
        if chat_id not in _last_inbox:
            api.send_message(chat_id, "ℹ️ Сначала откройте «инбокс», затем выберите номер карточки.")
            return True
        idx = int(m_reply.group(2))
        body = m_reply.group(3).strip()
        items = _last_inbox.get(chat_id, [])
        if 1 <= idx <= len(items):
            _inbox_reply(api, chat_id, items[idx - 1], body)
        else:
            api.send_message(chat_id, f"❌ Нет карточки №{idx} в последнем инбоксе.")
        return True

    if any(phrase in t for phrase in ("озвучь инбокс", "озвучь всё", "голосом инбокс", "прочитай инбокс вслух")):
        api.send_message(chat_id, "⏳ Собираю карточки для озвучки…")
        items, _summary = _collect_inbox({})
        if not items:
            api.send_message(chat_id, "📭 Инбокс пуст.")
        else:
            _last_inbox[chat_id] = items
            _last_inbox_filters[chat_id] = {}
            _inbox_voice(api, chat_id, items)
        return True

    m_search = re.match(r"^(найди во всех|ищи везде|найди везде|поиск по всем)\s*(?:чатах|сообщениях|каналах)?\s*:?\s*(.+)$", text, re.IGNORECASE)
    if m_search:
        query = m_search.group(2).strip()
        if query:
            api.send_message(chat_id, f"🔍 Ищу «{_esc_tg(query)}» по подключённым каналам…")
            _inbox_search(api, chat_id, query)
        else:
            api.send_message(chat_id, "🔍 Формат: «найди во всех чатах &lt;запрос&gt;»")
        return True

    inbox_terms = ("инбокс", "inbox", "все сообщения", "всё в одном", "сводка сообщений", "где что новое", "проверь всё")
    if any(term in t for term in inbox_terms):
        _send_unified_inbox(api, chat_id, text)
        return True
    return False


def _android_gateway_run(args: list[str], timeout: int = 60) -> dict:
    """Вызвать локальный Android gateway и разобрать JSON без shell-инъекций."""
    import subprocess as _sp
    try:
        result = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_android_gateway.py"), *args],
                         capture_output=True, text=True, timeout=timeout, cwd=str(PROJECT_ROOT),
                         env={**os.environ, "AIOS_ADB_BIN": "/usr/local/bin/aios-adb"})
        out = (result.stdout or "").strip()
        start = out.find("{")
        return json.loads(out[start:]) if start >= 0 else {"status": "error", "error": (result.stderr or out)[-250:]}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}


# Последние показанные безопасные карточки потенциальных лидов: chat_id -> rows.
_last_phone_leads: dict[int, list[dict]] = {}
# Последние показанные metadata-only CRM follow-up задачи телефона.
_last_phone_crm_tasks: dict[int, list[dict]] = {}
# Последние показанные metadata-only задачи банковских уведомлений.
_last_bank_tasks: dict[int, list[dict]] = {}


def _handle_phone_bank_monitor_intent(api, chat_id: int, text: str) -> bool:
    raw = str(text or "").strip()
    t = " ".join(raw.casefold().split())
    task_scope = any(phrase in t for phrase in ("банковские задачи", "задачи банков", "задачи банка"))
    review = re.search(r"(?:отметь|закрой|обработай)\s+банковск\w*\s+задач\w*\s*#?(\d+)", raw, re.IGNORECASE)
    bank_scope = any(phrase in t for phrase in ("банки телефона", "статус банков телефона", "банковские уведомления телефона", "банки android"))
    if not (task_scope or review or bank_scope or (chat_id in _last_bank_tasks and "банковск" in t)):
        return False
    try:
        from aios_core.android_bank_monitor import AndroidBankMonitor, format_telegram
        monitor = AndroidBankMonitor(PROJECT_ROOT)
        if review:
            tasks = _last_bank_tasks.get(chat_id) or []
            index = int(review.group(1))
            if not 1 <= index <= len(tasks):
                api.send_message(chat_id, "ℹ️ Сначала откройте «банковские задачи телефона», затем укажите номер.")
                return True
            _pending_confirm[chat_id] = {"kind": "bank_task_review", "data": {"task_id": tasks[index - 1].get("id")}}
            api.send_message(chat_id, "🏦 Отметить локальную задачу банковского уведомления обработанной?\n«да» / «нет»")
            return True
        if task_scope:
            tasks = monitor.list_tasks(limit=30)
            _last_bank_tasks[chat_id] = tasks
            if not tasks:
                api.send_message(chat_id, "🏦 <b>Банковские задачи телефона</b>\nОткрытых задач на проверку нет.")
                return True
            summary = monitor.task_summary()
            lines = [
                "🏦 <b>БАНКОВСКИЕ ЗАДАЧИ ТЕЛЕФОНА</b>",
                f"<i>Открыты: {summary.get('pending', len(tasks))} · внимание: {summary.get('attention', 0)} · просрочены: {summary.get('overdue', 0)}</i>",
                "━━━━━━━━━━━━━━━━",
            ]
            age_label = {"fresh": "🟢 Новая", "attention": "🟠 Внимание", "overdue": "🔴 Просрочена", "unknown": "⚪ Без времени"}
            for index, task in enumerate(tasks[:12], 1):
                source = _esc_tg(str(task.get("source") or "Банк"))
                observed = _esc_tg(str(task.get("observed_at") or "")[:19])
                age = age_label.get(str(task.get("age_state") or ""), "⚪ Без времени")
                lines.append(f"{index:02d}. <b>{source}</b> · {age} · 🕐 {observed}")
            lines.append("━━━━━━━━━━━━━━━━")
            lines.append("<i>«отметь банковскую задачу 1 обработанной» — закрыть локальную задачу. Суммы, карты и OTP не выводятся.</i>")
            api.send_message(chat_id, "\n".join(lines)[:3900])
            return True
        api.send_message(chat_id, format_telegram(monitor.snapshot()))
    except Exception:
        api.send_message(chat_id, "⚠️ Безопасный статус банков телефона временно недоступен.")
    return True


def _handle_phone_recovery_intent(api, chat_id: int, text: str) -> bool:
    t = " ".join(str(text or "").casefold().split())
    if not any(phrase in t for phrase in ("восстановление телефона", "диагностика телефона", "почини телефон", "проверка adb")):
        return False
    try:
        from aios_core.android_recovery import AndroidRecovery
        report = AndroidRecovery(PROJECT_ROOT).check()
        action = str(report.get("action") or "unknown")
        labels = {
            "none": "✅ Подключение ADB и AIOS Companion работают штатно.",
            "wireless_debug_endpoint_needed": "⚠️ Companion доступен, но требуется новый endpoint Беспроводной отладки.",
            "companion_restart_needed": "⚠️ ADB подключён, но AIOS Companion недоступен. Откройте Companion или перезапустите его на телефоне.",
            "phone_vpn_or_companion_needed": "⚠️ Телефон или WireGuard/Companion недоступны. Проверьте VPN и подключение телефона.",
        }
        api.send_message(chat_id, "🛠 <b>Восстановление телефона</b>\n" + labels.get(action, "⚠️ Нужна проверка подключения."))
    except Exception:
        api.send_message(chat_id, "⚠️ Диагностика телефона временно недоступна.")
    return True


def _handle_phone_weekly_report_intent(api, chat_id: int, text: str) -> bool:
    t = " ".join(str(text or "").casefold().split())
    if not any(phrase in t for phrase in ("недельный отчёт телефона", "недельный отчет телефона", "отчёт лидов за неделю", "отчет лидов за неделю", "недельная сводка телефона")):
        return False
    try:
        from run_phone_weekly_report import build_text
        api.send_message(chat_id, build_text(PROJECT_ROOT, days=7))
    except Exception:
        api.send_message(chat_id, "⚠️ Недельный отчёт телефона временно недоступен.")
    return True


def _handle_phone_control_center_intent(api, chat_id: int, text: str) -> bool:
    t = " ".join(str(text or "").casefold().split())
    if not any(phrase in t for phrase in ("центр телефона", "статус автоматизации телефона", "контроль телефона", "центр android")):
        return False
    try:
        from aios_core.phone_control_center import PhoneControlCenter, format_telegram
        api.send_message(chat_id, format_telegram(PhoneControlCenter(PROJECT_ROOT).snapshot()))
    except Exception:
        api.send_message(chat_id, "⚠️ Центр управления телефоном временно недоступен.")
    return True


def _handle_phone_audit_intent(api, chat_id: int, text: str) -> bool:
    """Render the metadata-only phone action log on explicit owner request."""
    t = " ".join(str(text or "").casefold().split())
    if not any(phrase in t for phrase in ("журнал телефона", "аудит телефона", "действия телефона", "логи телефона")):
        return False
    from aios_core.android_audit import PhoneActionAudit
    events = PhoneActionAudit(PROJECT_ROOT).recent(limit=20)
    if not events:
        api.send_message(chat_id, "📋 <b>Журнал телефона</b>\nБезопасных действий пока не зарегистрировано.")
        return True
    labels = {
        "app_open": "Открытие приложения", "app_ui_calibration": "Калибровка интерфейса",
        "messenger_chat_open": "Открытие чата", "messenger_draft": "Черновик сообщения",
        "messenger_send": "Отправка сообщения", "uklon_route": "Черновик Uklon",
        "uklon_route_query": "Поиск Uklon", "easyway_route": "Черновик EasyWay",
        "easyway_route_query": "Поиск EasyWay",
    }
    lines = ["📋 <b>БЕЗОПАСНЫЙ ЖУРНАЛ ТЕЛЕФОНА</b>", "━━━━━━━━━━━━━━━━"]
    for index, event in enumerate(events[-15:][::-1], 1):
        action = labels.get(str(event.get("action") or ""), str(event.get("action") or "действие"))
        status = _esc_tg(str(event.get("status") or "—"))
        package = _esc_tg(str(event.get("package") or ""))
        at = _esc_tg(str(event.get("at") or "")[:19])
        lines.append(f"{index:02d}. <b>{_esc_tg(action)}</b> · {status}" + (f" · <code>{package}</code>" if package else ""))
        lines.append(f"    🕐 {at}")
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append("<i>Журнал не содержит текста сообщений, имён, маршрутов, координат, фото, аудио или координат нажатий.</i>")
    api.send_message(chat_id, "\n".join(lines)[:3900])
    return True


def _phone_lead_queue():
    from aios_core.android_leads import AndroidLeadQueue
    return AndroidLeadQueue(PROJECT_ROOT)


def _handle_phone_lead_intent(api, chat_id: int, text: str) -> bool:
    """Privacy-preserving queue for WhatsApp/iMe notification contacts."""
    raw = str(text or "").strip()
    t = " ".join(raw.casefold().split())
    has_phone_scope = any(word in t for word in (
        "телефон", "android", "андроид", "whatsapp", "ватсап", "ime", "i.me", "айми", "име",
    ))
    has_lead_scope = any(stem in t for stem in ("лид", "обращен", "потенциальн"))
    has_task_scope = any(phrase in t for phrase in ("crm задач", "crm-задач", "crm follow", "follow-up", "задачи телефона"))
    # Follow-up commands may omit «телефон» only after this chat received a
    # metadata-only list. No message content is used for that resolution.
    if not ((has_lead_scope or has_task_scope) and (has_phone_scope or chat_id in _last_phone_leads or chat_id in _last_phone_crm_tasks)):
        return False
    queue = _phone_lead_queue()
    draft_from_task = re.search(
        r"(?:подготовь|сделай)\s+(?:черновик|ответ)\s+(?:по|для)\s+(?:crm\s*)?задач\w*\s*#?(\d+)\s+"
        r"(?:в\s+)?(whatsapp|ватсап|ватс\s*апп|вотсап|ime|i\.me|айми|име)\s*:\s*([^|]{1,100})\|\s*(.+)$",
        raw, re.IGNORECASE,
    )
    if draft_from_task:
        tasks = _last_phone_crm_tasks.get(chat_id) or []
        index = int(draft_from_task.group(1))
        if not 1 <= index <= len(tasks):
            api.send_message(chat_id, "ℹ️ Сначала откройте «CRM задачи телефона», затем укажите номер задачи.")
            return True
        app_token = draft_from_task.group(2).casefold()
        app = "ime" if app_token in ("ime", "i.me", "айми", "име") else "whatsapp"
        contact = draft_from_task.group(3).strip()
        body = draft_from_task.group(4).strip()
        if not contact or not body:
            api.send_message(chat_id, "ℹ️ Формат: «подготовь черновик по CRM задаче 1 в WhatsApp: Имя | Текст»")
            return True
        _pending_confirm[chat_id] = {"kind": "phone_crm_task_draft", "data": {
            "task_id": tasks[index - 1].get("id"), "app": app, "contact": contact, "text": body,
        }}
        api.send_message(chat_id,
                         "✍️ Открыть указанный чат и вставить черновик из CRM follow-up задачи?\n"
                         "Открытие чата может отметить его прочитанным; отправка потребует отдельного подтверждения. «да» / «нет»")
        return True
    complete = re.search(r"(?:закрой|заверши|выполни)\s+(?:crm\s*)?(?:задач\w*|follow[- ]?up)\s*#?(\d+)", raw, re.IGNORECASE)
    if complete:
        tasks = _last_phone_crm_tasks.get(chat_id) or []
        index = int(complete.group(1))
        if not 1 <= index <= len(tasks):
            api.send_message(chat_id, "ℹ️ Сначала откройте «CRM задачи телефона», затем укажите номер задачи.")
            return True
        _pending_confirm[chat_id] = {"kind": "phone_crm_task_complete", "data": {"task_id": tasks[index - 1].get("id")}}
        api.send_message(chat_id, "✅ Закрыть локальную CRM follow-up задачу?\n«да» / «нет»")
        return True
    if has_task_scope and not has_lead_scope:
        tasks = queue.list_crm_tasks(limit=30)
        _last_phone_crm_tasks[chat_id] = tasks
        if not tasks:
            api.send_message(chat_id, "📌 <b>CRM задачи телефона</b>\nОткрытых follow-up задач нет.")
            return True
        summary = queue.summary()
        lines = [
            "📌 <b>CRM FOLLOW-UP ЗАДАЧИ ТЕЛЕФОНА</b>",
            f"<i>Открыты: {summary.get('crm_open', len(tasks))} · внимание: {summary.get('crm_attention', 0)} · просрочены: {summary.get('crm_overdue', 0)}</i>",
            "━━━━━━━━━━━━━━━━",
        ]
        age_label = {"fresh": "🟢 Новая", "attention": "🟠 Внимание", "overdue": "🔴 Просрочена", "unknown": "⚪ Без времени"}
        for index, task in enumerate(tasks[:12], 1):
            source = _esc_tg(str(task.get("source") or "Телефон"))
            created = _esc_tg(str(task.get("created_at") or "")[:19])
            age = age_label.get(str(task.get("age_state") or ""), "⚪ Без времени")
            lines.append(f"╭─ <code>{index:02d}</code> 📌 <b>{source}</b> · {age}")
            lines.append("├ Открыть чат и вручную проверить обращение")
            lines.append(f"╰ 🕐 {created or 'время недоступно'}")
        lines.append("━━━━━━━━━━━━━━━━")
        lines.append("<i>«закрой CRM задачу 1» — закрыть локальную follow-up задачу. Клиенты и сообщения не создаются автоматически.</i>")
        api.send_message(chat_id, "\n".join(lines)[:3900])
        return True
    promote = re.search(r"(?:создай|добавь)\s+(?:crm\s*)?(?:задач\w*)\s+(?:для\s+)?(?:лид\w*|обращени\w*)\s*(?:телефона)?\s*#?(\d+)", raw, re.IGNORECASE)
    if promote:
        rows = _last_phone_leads.get(chat_id) or []
        index = int(promote.group(1))
        if not 1 <= index <= len(rows):
            api.send_message(chat_id, "ℹ️ Сначала откройте «лиды телефона», затем укажите номер карточки.")
            return True
        _pending_confirm[chat_id] = {"kind": "phone_lead_promote", "data": {"lead_id": rows[index - 1].get("id")}}
        api.send_message(chat_id,
                         "📌 Создать локальную CRM-задачу для этой карточки?\n"
                         "Клиент, имя, телефон и сообщение не будут созданы или переданы. «да» / «нет»")
        return True
    review = re.search(r"(?:обработай|отметь|закрой)\s+(?:лид|обращени\w*)\s*(?:телефона)?\s*#?(\d+)", raw, re.IGNORECASE)
    if review:
        rows = _last_phone_leads.get(chat_id) or []
        index = int(review.group(1))
        if not 1 <= index <= len(rows):
            api.send_message(chat_id, "ℹ️ Сначала откройте «лиды телефона», затем укажите номер карточки.")
            return True
        result = queue.review(str(rows[index - 1].get("id") or ""))
        if result.get("status") in ("reviewed", "already_reviewed"):
            api.send_message(chat_id, "✅ Лид отмечен как обработанный. CRM-клиент и сообщения не создавались.")
        else:
            api.send_message(chat_id, "⚠️ Не удалось обновить карточку лида.")
        return True
    # Refresh only the metadata-only queue; notification text/senders are never
    # requested or rendered by this handler.
    queue.sync()
    source = "WhatsApp" if any(word in t for word in ("whatsapp", "ватсап")) else \
             "iMe" if any(word in t for word in ("ime", "i.me", "айми", "име")) else ""
    rows = queue.list_pending(limit=20, source=source)
    _last_phone_leads[chat_id] = rows
    if not rows:
        api.send_message(chat_id, "📲 <b>Лиды телефона</b>\nНовых карточек для проверки нет.")
        return True
    summary = queue.summary()
    lines = ["📲 <b>ПОТЕНЦИАЛЬНЫЕ ЛИДЫ ТЕЛЕФОНА</b>",
             f"<i>Ожидают проверки: {summary.get('pending', len(rows))} · CRM-задач: {summary.get('crm_open', 0)}</i>",
             "━━━━━━━━━━━━━━━━"]
    for index, row in enumerate(rows[:12], 1):
        source_label = _esc_tg(str(row.get("source") or "Телефон"))
        observed = _esc_tg(str(row.get("observed_at") or "")[:19])
        lines.append(f"╭─ <code>{index:02d}</code> 📲 <b>{source_label}</b>")
        lines.append("├ Потенциальное новое обращение")
        lines.append(f"╰ 🕐 {observed or 'время недоступно'}")
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append("<i>Содержимое уведомлений, имена и номера не сохраняются здесь. «отметь лид 1 обработанным» — закрыть карточку; «создай CRM задачу для лида 1» — создать локальную follow-up задачу.</i>")
    api.send_message(chat_id, "\n".join(lines)[:3900])
    return True


def _phone_adapter(key: str):
    """Load a confirmed-workflow adapter without exposing Companion secrets."""
    from aios_core.android_gateway import AndroidGateway
    from aios_core.android_phone_workflows import adapter_for
    return adapter_for(key, AndroidGateway(PROJECT_ROOT))


def _phone_error(data: dict) -> str:
    """Safe error renderer: adapters must never return raw screen text here."""
    return _esc_tg(str(data.get("error") or data.get("status") or "неизвестная ошибка"))[:280]


def _mask_android_notification(value: object, limit: int = 180) -> str:
    """Never echo OTP/PIN/card-like data from a phone notification to Telegram."""
    value = str(value or "")
    value = re.sub(r"(?<!\d)(?:\d[ -]?){12,19}(?!\d)", "••••", value)
    value = re.sub(r"(?<!\d)\d{4,8}(?!\d)", "••••", value)
    return value[:limit]


def _send_phone_status(api, chat_id: int, adapter) -> None:
    data = adapter.status()
    title = _esc_tg(str(data.get("title") or "Приложение"))
    if data.get("status") == "not_installed":
        api.send_message(chat_id, f"➕ <b>{title}</b> не найден на телефоне.")
        return
    if data.get("status") != "ok":
        api.send_message(chat_id, f"⚠️ <b>{title}</b>: {_phone_error(data)}")
        return
    lines = [f"📱 <b>{title}</b>",
             f"Приложение: <b>{'доступно' if data.get('available') else 'не найдено'}</b>",
             f"Управление интерфейсом: <b>{'готово' if data.get('accessibility') else 'не разрешено'}</b>",
             f"Сейчас активно: <b>{'да' if data.get('active') else 'нет'}</b>"]
    if "notification_count" in data:
        lines.append(f"Новых служебных уведомлений: <b>{data.get('notification_count', 0)}</b>")
    if data.get("ui_calibrated"):
        controls = data.get("route_controls") or {}
        ready = bool(controls) and all(bool(value) for value in controls.values())
        lines.append("Интерфейс маршрута: <b>проверен</b>" if ready else "Интерфейс маршрута: <b>требует проверки</b>")
    if not data.get("ui_ready"):
        lines.append("⚠️ Для безопасной работы с интерфейсом требуется обновить AIOS Companion.")
    api.send_message(chat_id, "\n".join(lines))


def _handle_android_phone_workflow_intent(api, chat_id: int, text: str) -> bool:
    """Intent router for confirmation-gated phone app workflows.

    It deliberately runs before the generic Android app opener.  A phrase such
    as «открой чат WhatsApp» must not be reduced to an unscoped package launch.
    """
    raw = str(text or "").strip()
    t = " ".join(raw.casefold().split())
    if not t:
        return False
    whatsapp_words = ("whatsapp", "ватсап", "ватс апп", "вотсап", "watsapp")
    ime_words = ("ime", "i.me", "айми", "име мессенджер")
    easyway_words = ("easyway", "easy way", "изи вей", "изивей")
    abank_words = ("a-bank", "a bank", "абанк", "а-банк")
    privat_words = ("privat24", "приват24", "приват 24")
    has_whatsapp = any(word in t for word in whatsapp_words)
    has_ime = any(word in t for word in ime_words)
    has_uklon = "uklon" in t or "уклон" in t
    has_easyway = any(word in t for word in easyway_words)
    has_abank = any(word in t for word in abank_words)
    has_privat = any(word in t for word in privat_words)

    # ---- WhatsApp, only the Android phone application ----
    if has_whatsapp:
        adapter = _phone_adapter("whatsapp")
        if any(word in t for word in ("статус", "состояние", "готов", "подключ")):
            _send_phone_status(api, chat_id, adapter)
            return True
        if any(word in t for word in ("прочитай", "покажи сообщения", "покажи чат", "что в чате", "сообщения")):
            # The wording itself is an explicit request to read the currently
            # visible chat. The adapter masks OTP/card-like sequences.
            result = adapter.read_visible_chat()
            if result.get("status") != "ok":
                api.send_message(chat_id, f"⚠️ WhatsApp: {_phone_error(result)}")
            else:
                messages = result.get("messages") or []
                if not messages:
                    api.send_message(chat_id, "💬 WhatsApp: видимых сообщений не найдено.")
                else:
                    lines = ["💬 <b>WhatsApp · видимая часть текущего чата</b>"]
                    lines.extend(f"• {_esc_tg(item)}" for item in messages[-8:])
                    lines.append("\n<i>Коды и номера карт автоматически скрыты.</i>")
                    api.send_message(chat_id, "\n".join(lines)[:3900])
            return True
        # A draft is always inserted first and then needs a second confirmation
        # to press the actual send control.
        draft_match = re.search(
            r"(?:whatsapp|ватсап|ватс\s*апп|вотсап|watsapp)\s+"
            r"(?:черновик|подготовь\s+ответ|напиши|ответь)\s*[:—–-]\s*(.+)$",
            raw, re.IGNORECASE,
        )
        if not draft_match:
            draft_match = re.search(
                r"^(?:черновик|подготовь\s+ответ)\s+(?:в\s+)?"
                r"(?:whatsapp|ватсап|ватс\s*апп|вотсап|watsapp)\s*[:—–-]\s*(.+)$",
                raw, re.IGNORECASE,
            )
        if draft_match:
            body = draft_match.group(1).strip()
            if not body:
                api.send_message(chat_id, "✍️ Формат: «WhatsApp черновик: текст ответа»")
                return True
            _pending_confirm[chat_id] = {"kind": "whatsapp_draft", "data": {"text": body}}
            api.send_message(chat_id,
                             f"✍️ Вставить черновик в <b>текущий открытый чат WhatsApp</b>?\n"
                             f"Текст: «{_esc_tg(body[:300])}»\n\n"
                             "После вставки будет отдельное подтверждение отправки. «да» / «нет»")
            return True
        chat_match = re.search(
            r"(?:открой|найди)\s+(?:чат\s+)?(?:в\s+)?"
            r"(?:whatsapp|ватсап|ватс\s*апп|вотсап|watsapp)\s*(?:чат)?\s*[:—–-]?\s*(.+)$",
            raw, re.IGNORECASE,
        )
        if not chat_match:
            chat_match = re.search(
                r"(?:whatsapp|ватсап|ватс\s*апп|вотсап|watsapp)\s+"
                r"(?:открой|найди)\s+чат\s*[:—–-]?\s*(.+)$",
                raw, re.IGNORECASE,
            )
        if chat_match:
            contact = chat_match.group(1).strip(" .,:;—–-")
            if not contact:
                api.send_message(chat_id, "💬 Формат: «открой чат WhatsApp: Имя»")
                return True
            _pending_confirm[chat_id] = {"kind": "whatsapp_open_chat", "data": {"contact": contact}}
            api.send_message(chat_id,
                             f"💬 Открыть чат WhatsApp «<b>{_esc_tg(contact[:100])}</b>»?\n"
                             "Это может пометить чат как прочитанный. «да» / «нет»")
            return True
        if any(word in t for word in ("открой", "запусти")):
            _pending_confirm[chat_id] = {"kind": "phone_open_adapter", "data": {"app": "whatsapp"}}
            api.send_message(chat_id, "📱 Открыть WhatsApp на телефоне? «да» / «нет»")
            return True
        api.send_message(chat_id,
                         "💬 <b>WhatsApp на телефоне</b>\n"
                         "• «WhatsApp статус»\n"
                         "• «открой чат WhatsApp: Имя»\n"
                         "• «WhatsApp черновик: текст» — затем отдельное подтверждение отправки\n"
                         "• «прочитай WhatsApp» — только видимый текущий чат")
        return True

    # ---- iMe: draft only in a chat opened manually on the phone ----
    if has_ime:
        adapter = _phone_adapter("ime")
        if any(word in t for word in ("статус", "состояние", "готов", "подключ")):
            _send_phone_status(api, chat_id, adapter)
            return True
        draft_match = re.search(r"(?:ime|i\.me|айми|име\s+мессенджер)\s+(?:черновик|напиши|ответь)\s*[:—–-]\s*(.+)$", raw, re.IGNORECASE)
        if draft_match:
            body = draft_match.group(1).strip()
            _pending_confirm[chat_id] = {"kind": "ime_draft", "data": {"text": body}}
            api.send_message(chat_id,
                             f"✍️ Вставить черновик в текущий открытый чат iMe?\n«{_esc_tg(body[:300])}»\n\n"
                             "Отправка будет подтверждаться отдельно. «да» / «нет»")
            return True
        chat_match = re.search(
            r"(?:открой|найди)\s+(?:чат\s+)?(?:в\s+)?"
            r"(?:ime|i\.me|айми|име\s+мессенджер)\s*(?:чат)?\s*[:—–-]?\s*(.+)$",
            raw, re.IGNORECASE,
        )
        if not chat_match:
            chat_match = re.search(
                r"(?:ime|i\.me|айми|име\s+мессенджер)\s+"
                r"(?:открой|найди)\s+чат\s*[:—–-]?\s*(.+)$",
                raw, re.IGNORECASE,
            )
        if chat_match:
            contact = chat_match.group(1).strip(" .,:;—–-")
            if not contact:
                api.send_message(chat_id, "💬 Формат: «открой чат iMe: Имя»")
                return True
            _pending_confirm[chat_id] = {"kind": "ime_open_chat", "data": {"contact": contact}}
            api.send_message(chat_id,
                             f"💬 Открыть чат iMe «<b>{_esc_tg(contact[:100])}</b>»?\n"
                             "Это может пометить чат как прочитанный. «да» / «нет»")
            return True
        if any(word in t for word in ("открой", "запусти")):
            _pending_confirm[chat_id] = {"kind": "phone_open_adapter", "data": {"app": "ime"}}
            api.send_message(chat_id, "📱 Открыть iMe Messenger на телефоне? «да» / «нет»")
            return True
        api.send_message(chat_id,
                         "💬 <b>iMe Messenger</b>\n"
                         "• «iMe статус»\n• «открой чат iMe: Имя»\n"
                         "• «iMe черновик: текст» — отправка только после второго подтверждения")
        return True

    # ---- Uklon: never books/orders a ride automatically ----
    if has_uklon:
        adapter = _phone_adapter("uklon")
        if any(phrase in t for phrase in ("продолжи маршрут", "продолжить маршрут")):
            route = _phone_route_drafts.get(chat_id) or {}
            route_id = str(route.get("route_id") or "")
            field = str(route.get("next_field") or "")
            if not route_id or field not in ("pickup", "destination"):
                api.send_message(chat_id, "ℹ️ Сначала создайте черновик: «маршрут Uklon: откуда -> куда».")
                return True
            _pending_confirm[chat_id] = {"kind": "uklon_enter_route_query", "data": {"route_id": route_id, "field": field}}
            label = "точку отправления" if field == "pickup" else "пункт назначения"
            api.send_message(chat_id,
                             f"🚕 Ввести подготовленный поисковый запрос для «{label}» в Uklon?\n"
                             "AIOS не будет выбирать подсказку и не создаст заказ. «да» / «нет»")
            return True
        if any(word in t for word in ("калибр", "проверь интерфейс", "настрой интерфейс")):
            _pending_confirm[chat_id] = {"kind": "phone_calibrate", "data": {"app": "uklon"}}
            api.send_message(chat_id, "🚕 Открыть Uklon Passenger и проверить только элементы маршрута без заказа поездки? «да» / «нет»")
            return True
        if any(word in t for word in ("статус", "состояние", "уведомлен", "готов")):
            _send_phone_status(api, chat_id, adapter)
            return True
        route_match = re.search(r"(?:маршрут|поездк\w*)\s+(?:uklon|уклон)\s*[:—–-]?\s*(.*?)\s*(?:->|→|в|до)\s+(.+)$", raw, re.IGNORECASE)
        if route_match:
            pickup, destination = route_match.group(1).strip(), route_match.group(2).strip()
            _pending_confirm[chat_id] = {"kind": "uklon_stage_route", "data": {"pickup": pickup, "destination": destination}}
            api.send_message(chat_id,
                             "🚕 Открыть Uklon Passenger и подготовить <b>черновик маршрута</b>?\n"
                             "Заказ, принятие поездки и любые списания не создаются. «да» / «нет»")
            return True
        if "driver" in t or "водител" in t:
            _pending_confirm[chat_id] = {"kind": "uklon_open_driver", "data": {}}
            api.send_message(chat_id, "🚕 Открыть Uklon Driver на телефоне? «да» / «нет»")
            return True
        if any(word in t for word in ("открой", "запусти")):
            _pending_confirm[chat_id] = {"kind": "phone_open_adapter", "data": {"app": "uklon"}}
            api.send_message(chat_id, "🚕 Открыть Uklon Passenger на телефоне? «да» / «нет»")
            return True
        api.send_message(chat_id, "🚕 Uklon: «Uklon статус», «открой Uklon», «маршрут Uklon: откуда -> куда». Заказ поездки всегда остаётся ручным подтверждаемым действием.")
        return True

    # ---- EasyWay: package com.eway, now registered as installed ----
    if has_easyway:
        adapter = _phone_adapter("easyway")
        if any(word in t for word in ("калибр", "проверь интерфейс", "настрой интерфейс")):
            _pending_confirm[chat_id] = {"kind": "phone_calibrate", "data": {"app": "easyway"}}
            api.send_message(chat_id, "🚌 Открыть EasyWay и проверить только элемент поиска маршрута без запроса геолокации? «да» / «нет»")
            return True
        if any(word in t for word in ("статус", "состояние", "готов", "подключ")):
            _send_phone_status(api, chat_id, adapter)
            return True
        route_match = re.search(r"(?:маршрут|остановк\w*|транспорт)\s+(?:easyway|easy\s+way|изи\s*вей|изивей)\s*[:—–-]\s*(.+)$", raw, re.IGNORECASE)
        if route_match:
            destination = route_match.group(1).strip()
            _pending_confirm[chat_id] = {"kind": "easyway_stage_route", "data": {"destination": destination}}
            api.send_message(chat_id,
                             "🚌 Открыть EasyWay и подготовить приватный черновик маршрута?\n"
                             "Геолокация не включается и не отслеживается в фоне. «да» / «нет»")
            return True
        if any(word in t for word in ("открой", "запусти")):
            _pending_confirm[chat_id] = {"kind": "phone_open_adapter", "data": {"app": "easyway"}}
            api.send_message(chat_id, "🚌 Открыть EasyWay на телефоне? «да» / «нет»")
            return True
        api.send_message(chat_id, "🚌 EasyWay подключён как <code>com.eway</code>. Команды: «EasyWay статус», «открой EasyWay», «маршрут EasyWay: остановка или адрес».")
        return True

    # ---- Financial applications: monitoring/status/open only ----
    if has_abank or has_privat:
        app = "abank" if has_abank else "privat24"
        adapter = _phone_adapter(app)
        if any(word in t for word in ("статус", "состояние", "уведомлен", "готов", "подключ")):
            _send_phone_status(api, chat_id, adapter)
            api.send_message(chat_id, "🔒 Банковый режим: только мониторинг уведомлений и подтверждаемое открытие. Платежи, OTP, карты, биометрия и переводы не автоматизируются.")
            return True
        if any(word in t for word in ("открой", "запусти")):
            _pending_confirm[chat_id] = {"kind": "phone_open_adapter", "data": {"app": app}}
            api.send_message(chat_id, f"🏦 Открыть <b>{_esc_tg(adapter.title)}</b> на телефоне? «да» / «нет»")
            return True
        api.send_message(chat_id, f"🏦 {adapter.title}: «{adapter.title} статус» или «открой {adapter.title}». Финансовые операции отключены.")
        return True

    return False


def _cancel_phone_pending(api, chat_id: int, kind: str, data: dict) -> bool:
    if kind not in ("whatsapp_send_draft", "ime_send_draft"):
        return False
    try:
        app = "whatsapp" if kind == "whatsapp_send_draft" else "ime"
        adapter = _phone_adapter(app)
        adapter.cancel_draft(str(data.get("draft_id") or ""))
    except Exception:
        pass
    api.send_message(chat_id, "🚫 Отправка отменена. Текст на экране телефона не удалялся автоматически.")
    return True


def _confirm_phone_pending(api, chat_id: int, kind: str, data: dict) -> bool:
    """Perform one already-confirmed app step; return True when handled."""
    try:
        if kind == "bank_task_review":
            from aios_core.android_bank_monitor import AndroidBankMonitor
            result = AndroidBankMonitor(PROJECT_ROOT).review_task(str(data.get("task_id") or ""))
            if result.get("status") in ("reviewed", "already_reviewed"):
                api.send_message(chat_id, "✅ Локальная банковская задача отмечена обработанной. Финансовых действий не выполнялось.")
            else:
                api.send_message(chat_id, "⚠️ Не удалось обновить банковскую задачу.")
            return True
        if kind == "phone_crm_task_draft":
            app = str(data.get("app") or "")
            adapter = _phone_adapter(app)
            if not adapter:
                api.send_message(chat_id, "⚠️ Неизвестный мессенджер для CRM-задачи.")
                return True
            opened = adapter.open_chat(str(data.get("contact") or ""), confirm=True)
            if opened.get("status") != "opened":
                api.send_message(chat_id, f"⚠️ {_esc_tg(adapter.title)}: {_phone_error(opened)}")
                return True
            drafted = adapter.prepare_draft(str(data.get("text") or ""), confirm=True)
            if drafted.get("status") != "draft_ready":
                api.send_message(chat_id, f"⚠️ Черновик не подготовлен: {_phone_error(drafted)}")
                return True
            send_kind = "ime_send_draft" if app == "ime" else "whatsapp_send_draft"
            _pending_confirm[chat_id] = {"kind": send_kind, "data": {"draft_id": drafted.get("draft_id")}}
            api.send_message(chat_id,
                             "✅ Черновик из CRM follow-up задачи вставлен и проверен. Отправить его сейчас? Это отдельное действие. «да» / «нет»")
            return True
        if kind == "phone_crm_task_complete":
            result = _phone_lead_queue().complete_crm_task(str(data.get("task_id") or ""))
            if result.get("status") in ("completed", "already_completed"):
                api.send_message(chat_id, "✅ Локальная CRM follow-up задача закрыта. Сообщения и клиенты не изменялись.")
            else:
                api.send_message(chat_id, "⚠️ Не удалось закрыть CRM follow-up задачу.")
            return True
        if kind == "phone_lead_promote":
            result = _phone_lead_queue().promote_to_crm_task(str(data.get("lead_id") or ""))
            if result.get("status") in ("crm_task_created", "already_promoted"):
                api.send_message(chat_id,
                                 "✅ Локальная CRM-задача создана. Откройте нужный чат вручную и используйте подтверждаемый черновик ответа. Клиент и сообщение не создавались автоматически.")
            else:
                api.send_message(chat_id, "⚠️ Не удалось создать CRM-задачу для лида.")
            return True
        if kind == "phone_calibrate":
            adapter = _phone_adapter(str(data.get("app") or ""))
            if not adapter:
                api.send_message(chat_id, "⚠️ Неизвестное приложение телефона.")
                return True
            result = adapter.calibrate(confirm=True)
            if result.get("status") == "calibrated":
                selectors = result.get("selectors") or {}
                ready = bool(selectors) and all(bool(value) for value in selectors.values())
                api.send_message(chat_id,
                                 f"✅ Интерфейс <b>{_esc_tg(adapter.title)}</b> проверен: "
                                 f"{'маршрутные элементы найдены' if ready else 'элементы маршрута не найдены; ничего не вводилось'}.")
            else:
                api.send_message(chat_id, f"⚠️ {_esc_tg(adapter.title)}: {_phone_error(result)}")
            return True
        if kind == "phone_open_adapter":
            adapter = _phone_adapter(str(data.get("app") or ""))
            if not adapter:
                api.send_message(chat_id, "⚠️ Неизвестное приложение телефона.")
                return True
            result = adapter.open(confirm=True)
            if result.get("status") == "ok":
                api.send_message(chat_id, f"✅ На телефоне открыт <b>{_esc_tg(adapter.title)}</b>.")
            else:
                api.send_message(chat_id, f"⚠️ {_esc_tg(adapter.title)}: {_phone_error(result)}")
            return True
        if kind == "whatsapp_open_chat":
            adapter = _phone_adapter("whatsapp")
            result = adapter.open_chat(str(data.get("contact") or ""), confirm=True)
            if result.get("status") == "opened":
                api.send_message(chat_id, "✅ Чат WhatsApp открыт. Автоматическая отправка выключена.")
            else:
                api.send_message(chat_id, f"⚠️ WhatsApp: {_phone_error(result)}")
            return True
        if kind == "ime_open_chat":
            adapter = _phone_adapter("ime")
            result = adapter.open_chat(str(data.get("contact") or ""), confirm=True)
            if result.get("status") == "opened":
                api.send_message(chat_id, "✅ Чат iMe открыт. Автоматическая отправка выключена.")
            else:
                api.send_message(chat_id, f"⚠️ iMe: {_phone_error(result)}")
            return True
        if kind in ("whatsapp_draft", "ime_draft"):
            app = "whatsapp" if kind == "whatsapp_draft" else "ime"
            adapter = _phone_adapter(app)
            result = adapter.prepare_draft(str(data.get("text") or ""), confirm=True)
            if result.get("status") != "draft_ready":
                api.send_message(chat_id, f"⚠️ {_esc_tg(adapter.title)}: {_phone_error(result)}")
                return True
            send_kind = "whatsapp_send_draft" if app == "whatsapp" else "ime_send_draft"
            _pending_confirm[chat_id] = {"kind": send_kind, "data": {"draft_id": result.get("draft_id")}}
            api.send_message(chat_id,
                             "✍️ Черновик вставлен и проверен в поле ввода телефона.\n"
                             "<b>Отправить его сейчас?</b> Это отдельное действие. «да» / «нет»")
            return True
        if kind in ("whatsapp_send_draft", "ime_send_draft"):
            app = "whatsapp" if kind == "whatsapp_send_draft" else "ime"
            adapter = _phone_adapter(app)
            result = adapter.send_draft(str(data.get("draft_id") or ""), confirm=True)
            if result.get("status") == "send_tapped":
                api.send_message(chat_id,
                                 "✅ Нажатие «Отправить» выполнено на телефоне. Это не является гарантией доставки — проверьте статус в приложении.")
            else:
                api.send_message(chat_id, f"⚠️ Отправка заблокирована: {_phone_error(result)}")
            return True
        if kind == "uklon_open_driver":
            adapter = _phone_adapter("uklon")
            result = adapter.open_driver(confirm=True)
            if result.get("status") == "ok":
                api.send_message(chat_id, "✅ На телефоне открыт Uklon Driver.")
            else:
                api.send_message(chat_id, f"⚠️ Uklon Driver: {_phone_error(result)}")
            return True
        if kind == "uklon_stage_route":
            adapter = _phone_adapter("uklon")
            pickup = str(data.get("pickup") or "")
            result = adapter.stage_route(pickup, str(data.get("destination") or ""), confirm=True)
            if result.get("status") == "route_staged":
                controls = result.get("controls") or {}
                ready = bool(controls) and all(bool(value) for value in controls.values())
                if ready:
                    field = "pickup" if pickup.strip() else "destination"
                    _phone_route_drafts[chat_id] = {"route_id": result.get("route_id"), "next_field": field}
                    _pending_confirm[chat_id] = {"kind": "uklon_enter_route_query", "data": {"route_id": result.get("route_id"), "field": field}}
                    label = "точку отправления" if field == "pickup" else "пункт назначения"
                    api.send_message(chat_id,
                                     f"🚕 Черновик маршрута готов. Ввести поисковый запрос для «{label}»?\n"
                                     "Это только ввод текста: подсказка и заказ не выбираются. «да» / «нет»")
                else:
                    api.send_message(chat_id, "🚕 Черновик Uklon сохранён, но элементы адресов не подтверждены. Заказ поездки <b>не создан</b>.")
            else:
                api.send_message(chat_id, f"⚠️ Uklon: {_phone_error(result)}")
            return True
        if kind == "uklon_enter_route_query":
            adapter = _phone_adapter("uklon")
            field = str(data.get("field") or "")
            result = adapter.prepare_address_query(str(data.get("route_id") or ""), field, confirm=True)
            if result.get("status") == "query_entered":
                if field == "pickup":
                    route = _phone_route_drafts.setdefault(chat_id, {"route_id": data.get("route_id")})
                    route["next_field"] = "destination"
                    api.send_message(chat_id,
                                     "✅ Запрос точки отправления введён. Выберите точную подсказку <b>вручную на телефоне</b>, затем напишите «продолжи маршрут Uklon». Заказ не создавался.")
                else:
                    _phone_route_drafts.pop(chat_id, None)
                    api.send_message(chat_id,
                                     "✅ Запрос пункта назначения введён. Выберите точную подсказку <b>вручную на телефоне</b>; заказ поездки не создавался.")
            else:
                api.send_message(chat_id, f"⚠️ Uklon: {_phone_error(result)}")
            return True
        if kind == "easyway_stage_route":
            adapter = _phone_adapter("easyway")
            result = adapter.stage_route(str(data.get("destination") or ""), confirm=True)
            if result.get("status") == "route_staged":
                controls = result.get("controls") or {}
                ready = bool(controls) and all(bool(value) for value in controls.values())
                if ready:
                    _pending_confirm[chat_id] = {"kind": "easyway_enter_route_query", "data": {"route_id": result.get("route_id")}}
                    api.send_message(chat_id,
                                     "🚌 Черновик маршрута готов. Ввести поисковый запрос в EasyWay?\n"
                                     "Маршрут и геолокация не будут выбраны автоматически. «да» / «нет»")
                else:
                    api.send_message(chat_id, "🚌 Черновик EasyWay сохранён, но поле маршрута не подтверждено. Геолокация не отслеживается в фоне.")
            else:
                api.send_message(chat_id, f"⚠️ EasyWay: {_phone_error(result)}")
            return True
        if kind == "easyway_enter_route_query":
            adapter = _phone_adapter("easyway")
            result = adapter.prepare_destination_query(str(data.get("route_id") or ""), confirm=True)
            if result.get("status") == "query_entered":
                api.send_message(chat_id,
                                 "✅ Поисковый запрос введён в EasyWay. Выберите остановку или маршрут <b>вручную на телефоне</b>; геолокация не запрашивалась.")
            else:
                api.send_message(chat_id, f"⚠️ EasyWay: {_phone_error(result)}")
            return True
    except Exception as exc:
        api.send_message(chat_id, f"⚠️ Ошибка сценария телефона: {_esc_tg(str(exc))[:220]}")
        return True
    return False


def _handle_android_gateway_intent(api, chat_id: int, text: str) -> bool:
    """Детерминированные безопасные команды реального Android-адаптера."""
    raw = str(text or "").strip()
    t = " ".join(raw.casefold().split())
    phone_words = ("телефон", "android", "андроид", "смартфон")
    if not any(word in t for word in phone_words):
        return False
    if any(phrase in t for phrase in ("статус телефона", "телефон статус", "android статус", "статус android", "состояние телефона")):
        data = _android_gateway_run(["status"])
        if data.get("status") == "ok":
            api.send_message(chat_id,
                             "📱 <b>Android Device Adapter</b>\n"
                             f"Статус: <b>{'подключён' if data.get('connected') else 'офлайн'}</b>\n"
                             f"Устройство: {_esc_tg(data.get('name') or data.get('model') or '—')}\n"
                             f"Android: {data.get('android') or '—'} · заряд: {data.get('battery', '—')}%\n"
                             f"Экран: {_esc_tg(data.get('screen') or '—')}\n"
                             f"Приложений: {data.get('packages', '—')}")
        else:
            api.send_message(chat_id, f"⚠️ Android gateway: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    if any(phrase in t for phrase in ("управление приложениями телефона", "доступность телефона", "accessibility телефона")):
        data = _android_gateway_run(["accessibility"])
        if data.get("status") == "ok":
            api.send_message(chat_id, "🧩 Управление интерфейсом приложений: " + ("<b>разрешено</b>" if data.get("enabled") else "<b>не разрешено</b>"))
        else:
            api.send_message(chat_id, f"⚠️ Accessibility недоступен: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    if any(phrase in t for phrase in ("уведомления телефона", "уведомления android", "уведомления андроид")):
        data = _android_gateway_run(["notifications"])
        notices = data.get("notifications") or []
        if data.get("status") == "ok" and notices:
            lines = ["🔔 <b>Последние уведомления телефона</b>"]
            for notice in notices[-15:]:
                # Even an explicitly requested notification list must not leak
                # OTP/PIN/card-like values from the live Companion stream.
                lines.append(f"• <code>{_esc_tg(str(notice.get('package') or ''))}</code>\n"
                             f"  <b>{_esc_tg(_mask_android_notification(notice.get('title'), 100))}</b>\n"
                             f"  {_esc_tg(_mask_android_notification(notice.get('text'), 180))}")
            api.send_message(chat_id, "\n".join(lines)[:3900])
        elif data.get("status") == "ok":
            api.send_message(chat_id, "🔔 Уведомлений пока нет. Проверьте, что в Companion включён доступ к уведомлениям.")
        else:
            api.send_message(chat_id, f"⚠️ Уведомления недоступны: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    if any(phrase in t for phrase in ("статус камеры телефона", "статус микрофона телефона", "статус камеры и микрофона", "готовность камеры")):
        data = _android_gateway_run(["capture-status"])
        if data.get("status") == "ok":
            camera = bool(data.get("camera_permission"))
            microphone = bool(data.get("microphone_permission"))
            background = bool(data.get("background_capture"))
            api.send_message(chat_id,
                             "📷 <b>Камера и микрофон телефона</b>\n"
                             f"Камера: {'✅ разрешена' if camera else '⚪ не разрешена'}\n"
                             f"Микрофон: {'✅ разрешён' if microphone else '⚪ не разрешён'}\n"
                             f"Фоновый захват: {'⚠️ включён' if background else '✅ выключен'}\n"
                             "Фото и аудио не записываются этим статусом.")
        else:
            api.send_message(chat_id, f"⚠️ Статус камеры/микрофона недоступен: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    if any(phrase in t for phrase in ("статус геолокации телефона", "готовность геолокации", "геолокация доступна")):
        data = _android_gateway_run(["location-status"])
        if data.get("status") == "ok":
            permission = bool(data.get("permission"))
            ready = bool(data.get("ready"))
            gps = bool(data.get("gps_enabled"))
            network = bool(data.get("network_enabled"))
            api.send_message(chat_id,
                             "📍 <b>Геолокация телефона</b>\n"
                             f"Разрешение: {'✅' if permission else '⚠️'}\n"
                             f"GPS: {'✅ включён' if gps else '⚪ выключен'} · сеть: {'✅ включена' if network else '⚪ выключена'}\n"
                             f"Готовность без запроса координат: {'✅' if ready else '⚠️'}")
        else:
            api.send_message(chat_id, f"⚠️ Статус геолокации недоступен: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    if any(phrase in t for phrase in ("геолокация телефона", "местоположение телефона", "где телефон", "локация телефона")):
        _pending_confirm[chat_id] = {"kind": "android_location", "data": {}}
        api.send_message(chat_id, "📍 Запросить текущую геолокацию телефона?\n\n«да» / «нет»")
        return True
    if any(phrase in t for phrase in ("файлы телефона", "файлы android", "загрузки телефона")):
        data = _android_gateway_run(["files"])
        if data.get("status") == "ok":
            lines = [f"📂 <b>{_esc_tg(data.get('directory') or '')}</b> · {data.get('count', 0)} файлов"]
            lines += [f"• {_esc_tg(name)}" for name in (data.get('files') or [])[:40]]
            api.send_message(chat_id, "\n".join(lines)[:3900])
        else:
            api.send_message(chat_id, f"⚠️ Файлы недоступны: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    m_pull = re.search(r"(?:скачай|загрузи)\s+с\s+(?:телефона|android|андроида)\s*:?\s*(/sdcard/(?:Download|Documents|Pictures|DCIM)/[^\s]+)", raw, re.IGNORECASE)
    if m_pull:
        path = m_pull.group(1)
        _pending_confirm[chat_id] = {"kind": "android_pull_file", "data": {"path": path}}
        api.send_message(chat_id, f"📥 Скачать с телефона <code>{_esc_tg(path)}</code>?\n\n«да» / «нет»")
        return True
    if any(phrase in t for phrase in ("рабочие приложения", "приложения для работы", "профили приложений", "телефон приложения работа")):
        data = _android_gateway_run(["profiles"])
        profiles = data.get("profiles") or []
        if data.get("status") == "ok":
            lines = ["📱 <b>Рабочие приложения телефона</b>"]
            for profile in profiles:
                state = "✅" if profile.get("available") else "➕"
                package = (profile.get("installed") or ["не установлено"])[0]
                sensitive = " · подтверждение обязательно" if profile.get("sensitive") else ""
                lines.append(f"{state} <b>{_esc_tg(profile.get('title'))}</b>\n"
                             f"  <code>{_esc_tg(package)}</code>\n"
                             f"  {_esc_tg(profile.get('mode'))}{sensitive}")
            api.send_message(chat_id, "\n".join(lines)[:3900])
        else:
            api.send_message(chat_id, f"⚠️ Профили недоступны: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    if any(phrase in t for phrase in ("приложения телефона", "список приложений", "приложения android", "андроид приложения")):
        data = _android_gateway_run(["apps"])
        if data.get("status") == "ok":
            apps = data.get("apps") or []
            lines = [f"📱 <b>Приложения Android</b> · всего: {data.get('count', 0)}"]
            lines += [f"• <code>{_esc_tg(app)}</code>" for app in apps[:35]]
            if len(apps) > 35:
                lines.append(f"… показаны первые 35 из {data.get('count', 0)}")
            api.send_message(chat_id, "\n".join(lines)[:3900])
        else:
            api.send_message(chat_id, f"⚠️ Не удалось получить приложения: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    if any(phrase in t for phrase in ("скрин телефона", "скриншот телефона", "снимок телефона", "экран телефона")):
        api.send_message(chat_id, "⏳ Получаю защищённый снимок экрана телефона…")
        data = _android_gateway_run(["screenshot"], timeout=90)
        if data.get("status") == "ok" and data.get("file"):
            api.send_photo(chat_id, data["file"], caption="📱 Снимок Android-экрана")
        else:
            api.send_message(chat_id, f"⚠️ Скриншот недоступен: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    if any(phrase in t for phrase in ("ui телефона", "структура интерфейса телефона", "дамп интерфейса телефона")):
        data = _android_gateway_run(["ui-dump"], timeout=90)
        if data.get("status") == "ok" and data.get("file"):
            api.send_document(chat_id, data["file"], caption="📱 UIAutomator dump Android")
        else:
            api.send_message(chat_id, f"⚠️ UI dump недоступен: {_esc_tg(data.get('error') or data.get('status') or '?')}")
        return True
    m_open = re.search(r"(?:открой|запусти)\s+(?:на\s+)?(?:телефоне|android|андроиде)\s*:?\s*([\w.]+)", raw, re.IGNORECASE)
    if m_open:
        package = m_open.group(1).strip()
        _pending_confirm[chat_id] = {"kind": "android_open_app", "data": {"package": package}}
        api.send_message(chat_id, f"📱 Открыть на телефоне <code>{_esc_tg(package)}</code>?\n\n«да» / «нет»")
        return True
    if any(phrase in t for phrase in ("телефон помощь", "android помощь", "помощь с телефоном")):
        api.send_message(chat_id,
                         "📱 <b>Android Adapter</b>\n"
                         "• «статус телефона»\n• «рабочие приложения»\n• «приложения телефона»\n"
                         "• «уведомления телефона»\n• «геолокация телефона»\n"
                         "• «файлы телефона»\n• «скрин телефона»\n• «ui телефона»\n"
                         "• «открой на телефоне com.android.settings»")
        return True
    return False


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
                if _cancel_phone_pending(api, chat_id, kind, pend.get("data") or {}):
                    return True
                api.send_message(chat_id, "🚫 Действие отменено.")
                return True
            if _confirm_phone_pending(api, chat_id, kind, pend.get("data") or {}):
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
            if kind == "olx_create":
                d = pend["data"]
                import subprocess as _sp
                _cmd_list = ["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_ad_gen.py"),
                             "create", d["part"], "--confirm"]
                _ph = _last_photo.get(chat_id, "")
                if _ph and os.path.exists(_ph):
                    _cmd_list += ["--photo", _ph]
                r = _sp.run(_cmd_list,
                            capture_output=True, text=True, timeout=240, cwd=str(PROJECT_ROOT))
                try:
                    data = json.loads((r.stdout or "").strip().split("\n")[-1])
                except Exception:
                    data = {"status": "error", "error": (r.stderr or r.stdout or "?")[-200:]}
                st = data.get("status")
                if st == "published":
                    txt = f"✅ <b>Объявление опубликовано на OLX!</b>\n{_esc_tg(data.get('title', ''))} — {data.get('price', '?')} грн\n{data.get('url', '')}"
                    _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                                     "screenshot": data.get("screenshot"),
                                                     "caption": "✅ Опубликовано"}, "")
                elif st == "draft_created":
                    txt = f"📝 <b>Черновик создан</b>: {_esc_tg(data.get('title', ''))}\n"
                    if data.get("screenshot"):
                        _acct_send_result(api, chat_id, {"status": "ok",
                                                         "text": txt,
                                                         "screenshot": data.get("screenshot"),
                                                         "caption": "📝 OLX черновик"}, "")
                    else:
                        api.send_message(chat_id, txt)
                elif st == "phone_not_confirmed":
                    api.send_message(chat_id, f"📱 {data.get('error', 'Нужно подтвердить телефон')}\n"
                                              f"Напишите «подтверди телефон OLX».")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "ttn_create":
                d = pend["data"]
                import subprocess as _sp
                r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_ttn.py"),
                             "create", d["detail"], d["cost"], d["recipient"], d["phone"],
                             d["city"], d["warehouse"], "--confirm"],
                            capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT))
                try:
                    data = json.loads((r.stdout or "").strip().split("\n")[-1])
                except Exception:
                    data = {"status": "error", "error": (r.stderr or "?")[-300:]}
                if data.get("status") == "ok":
                    lifecycle_line = ""
                    inventory = data.get("inventory") or {}
                    if data.get("task"):
                        lifecycle_line = (
                            f"\n\n📋 <b>Задача создана:</b> отправить товар по ТТН.\n"
                            f"После передачи в НП: «отправил {data.get('ttn')}»."
                        )
                    if inventory.get("status") == "error":
                        lifecycle_line += (f"\n⚠️ Резерв склада требует проверки: "
                                           f"{_esc_tg(inventory.get('error', '?'))}")
                    if data.get("sale_lifecycle_warning"):
                        lifecycle_line += (f"\n⚠️ Учёт продажи: "
                                           f"{_esc_tg(data.get('sale_lifecycle_warning'))}")
                    olx = data.get("olx") or {}
                    if olx.get("status") == "deactivated":
                        lifecycle_line += "\n🛒 Связанное объявление OLX снято с публикации."
                    elif olx.get("status") == "kept_active":
                        lifecycle_line += (f"\n🛒 Объявление OLX оставлено: в остатке ещё "
                                           f"{olx.get('available_qty')} шт.")
                    elif olx.get("status") in ("not_found", "ambiguous", "error"):
                        lifecycle_line += ("\n⚠️ Не удалось однозначно снять связанное объявление OLX: "
                                           "проверьте его вручную.")
                    api.send_message(chat_id,
                                     f"📦 <b>ТТН создана: {data.get('ttn')}</b>\n"
                                     f"Деталь: {_esc_tg(data.get('detail'))} · Стоимость: {data.get('cost')} грн\n"
                                     f"Получатель: {_esc_tg(data.get('recipient'))}\n"
                                     f"Отслеживание: «отследи {data.get('ttn')}»{lifecycle_line}")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', 'Ошибка')}")
                return True
            if kind == "olx_chat_reply":
                d = pend["data"]
                data = _run_account_control(["olx", "chat", "reply", d["to"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"✅ Ответ отправлен покупателю «{_esc_tg(d['to'])}».")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "olx_bulk":
                import subprocess as _sp
                api.send_message(chat_id, "⏳ Публикую объявления на OLX (по ~2-3 мин на каждое)…")
                r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_ad_gen.py"),
                             "export_sklad", "--confirm"],
                            capture_output=True, text=True, timeout=1500, cwd=str(PROJECT_ROOT))
                try:
                    data = json.loads((r.stdout or "").strip().split("\n")[-1])
                except Exception:
                    data = {"status": "error", "error": (r.stderr or r.stdout or "?")[-300:]}
                if data.get("status") == "ok":
                    lines = ["📦 <b>Выгрузка склада завершена</b>"]
                    for x in (data.get("results") or [])[:20]:
                        em = {"published": "✅", "draft": "📝", "error": "❌"}.get(x.get("status"), "❌")
                        lines.append(f"{em} {_esc_tg(x.get('name'))}: {x.get('status')} {x.get('error', '')[:60]}")
                    api.send_message(chat_id, "\n".join(lines)[:3900])
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', 'Ошибка выгрузки')}")
                return True
            if kind == "olx_delete":
                d = pend["data"]
                data = _run_account_control(["olx", "delete", d["ad_id"], "--confirm"])
                st = data.get("status")
                if st == "deleted":
                    api.send_message(chat_id, f"🗑 Объявление <b>{d['ad_id']}</b> удалено с OLX.")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "olx_edit":
                d = pend["data"]
                data = _run_account_control(["olx", "edit", d["ad_id"],
                                             "--title", d.get("title", ""),
                                             "--desc", d.get("description", ""),
                                             "--price", d.get("price", ""),
                                             "--confirm"])
                st = data.get("status")
                if st == "edited":
                    api.send_message(chat_id, f"✅ Объявление <b>{d['ad_id']}</b> отредактировано.")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "messages_send":
                d = pend["data"]
                data = _run_account_control(["messages", "send", d["to"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"✅ SMS отправлено на «{_esc_tg(d['to'])}».")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
                return True
            if kind == "ig_comment_reply":
                d = pend["data"]
                data = _run_account_control(["instagram", "comment_reply", d["code"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"💬 Комментарий отправлен к <code>{d['code']}</code>: «{d['text'][:120]}»")
                else:
                    api.send_message(chat_id, f"❌ {data.get('error', st)}")
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
            if kind == "android_open_app":
                d = pend["data"]
                data = _android_gateway_run(["open", d["package"], "--confirm"])
                if data.get("status") == "ok":
                    api.send_message(chat_id, f"✅ На телефоне открыт <code>{_esc_tg(d['package'])}</code>.")
                else:
                    api.send_message(chat_id, f"⚠️ Android: {_esc_tg(data.get('error') or data.get('status') or '?')}")
                return True
            if kind == "android_location":
                data = _android_gateway_run(["location", "--confirm"])
                if data.get("status") == "ok":
                    api.send_message(chat_id,
                                     "📍 <b>Геолокация телефона</b>\n"
                                     f"{data.get('latitude')}, {data.get('longitude')}\n"
                                     f"Точность: {data.get('accuracy_m', '—')} м")
                else:
                    api.send_message(chat_id, f"⚠️ Геолокация недоступна: {_esc_tg(data.get('error') or data.get('status') or '?')}")
                return True
            if kind == "android_pull_file":
                d = pend["data"]
                data = _android_gateway_run(["pull", d["path"], "--confirm"], timeout=150)
                if data.get("status") == "ok" and data.get("file"):
                    api.send_document(chat_id, data["file"], caption="📱 Файл с Android")
                else:
                    api.send_message(chat_id, f"⚠️ Не удалось скачать файл: {_esc_tg(data.get('error') or data.get('status') or '?')}")
                return True
            if kind == "signal_send":
                d = pend["data"]
                data = _run_account_control(["signal", "send", d["chat"], d["text"], "--confirm"])
                st = data.get("status")
                if st == "sent":
                    api.send_message(chat_id, f"✅ Отправлено в Signal <b>{d['chat']}</b>: «{d['text'][:150]}»")
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

    # Bank monitor, recovery, weekly report, phone center/audit and leads precede broad CRM words.
    if _handle_phone_bank_monitor_intent(api, chat_id, text):
        return True
    if _handle_phone_recovery_intent(api, chat_id, text):
        return True
    if _handle_phone_weekly_report_intent(api, chat_id, text):
        return True
    if _handle_phone_control_center_intent(api, chat_id, text):
        return True
    if _handle_phone_audit_intent(api, chat_id, text):
        return True
    if _handle_phone_lead_intent(api, chat_id, text):
        return True

    # Продажи с ТТН должны обрабатываться раньше широких regex-ов аккаунтов,
    # автопланировщика и свободного LLM-чата.
    if _handle_sales_lifecycle_intent(api, chat_id, text):
        return True

    # Инбокс имеет приоритет над широким детектором Direct: слова «сообщения»
    # и «прочитанные» не должны неожиданно открывать Instagram.
    if _handle_unified_inbox_intent(api, chat_id, text):
        return True

    # Dedicated app workflows must run before the generic Android intent.
    if _handle_android_phone_workflow_intent(api, chat_id, text):
        return True

    if _handle_android_gateway_intent(api, chat_id, text):
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
    other_words = ("вайбер", "вибер", "viber", "signal", "сигнал", "мессенджер", "messenger",
                   "опубликуй видео", "опубликуй ролик", "опубликуй в тикток",
                   "боту @", "команду боту", "команда боту",
                   "в телеге", "телеграм", "telegram", "тг",
                   "инбокс", "inbox", "все сообщения", "всё в одном", "сводка сообщений",
                   "где что новое", "проверь всё", "напомни", "напоминание",
                   "аналитик", "рост подписчик", "динамика", "статистика аккаунт",
                   "сколько прибавил", "тренд", "запланируй пост", "пост в тикток на",
                   "пост в инстаграм на", "расписание постов",
                   "озвучь инбокс", "озвучь всё", "голосом инбокс", "прочитай инбокс вслух",
                   "найди во всех", "ищи везде", "найди везде", "поиск по всем",
                   "отметь всё прочитанным", "всё прочитано", "отметь прочитанным",
                   "присылай инбокс", "пришли инбокс", "включи инбокс", "отключи инбокс",
                   "расписание инбокса",
                   "комментари", "коментар", "ответь на комментарий", "ответь в комментар",
                   "шаблон", "ответь клиенту", "быстрый ответ", "шаблоны",
                   "следи за ценой", "мониторинг цен", "цена на олх", "снизил",
                   "экспортируй", "выгрузи", "экспорт", "в excel", "в эксель",
                   "выгрузить в файл", "включи голосовые ответы", "отвечай голосом",
                   "включи голос", "выключи голосовые ответы", "отвечай текстом",
                   "выключи голос",
                   "запиши продажу", "запиши расход", "запиши трату", "продал за",
                   "купил за", "потратил", "сколько заработал", "прибыль", "финанс",
                   "учет", "учёт", "деньги за неделю", "деньги за месяц",
                   "мои операции", "операции",
                   "создай объявление", "создай объявлени", "новое объявление на олх",
                   "создай объявления", "напиши объявление",
                   "автоответ олх", "автоответ olx", "автоответ в олх",
                   "автоответ покупателям",
                   "подними объявления", "подними мои объявления", "обнови объявления",
                   "мои объявления олх", "мои объявления olx", "контроль объявлений",
                   "сколько объявлений",
                   "добавь деталь", "добавь на склад", "спиши деталь",
                   "что на складе", "склад", "найди деталь", "продал ",
                   "остатки", "инвентаризац", "сколько деталей",
                   "вечерний отчёт", "вечерний отчет", "итоги дня",
                   "отчёт за день", "отчет за день", "дневной отчёт",
                   "сделай объявление из фото", "объявление по фото", "фото в объявление",
                   "выложи по фото", "деталь по фото",
                   "создай гугл таблицу", "создай google таблицу", "в гугл таблицу",
                   "создай таблицу из финансов", "создай таблицу из склада",
                   "сколько стоит", "почём", "цена на", "что стоит",
                   "распознай деталь", "что за деталь", "определи деталь",
                   "оцени деталь", "узнай деталь",
                   "кто продаёт дешевле", "кто продает дешевле", "где дешевле",
                   "топ выгодных", "лучшая цена",
                   "месячный отчёт", "месячный отчет", "отчёт за месяц",
                   "отчет за месяц", "отчёт за 30 дней", "сводка за месяц",
                   "подтверди телефон олх", "подтверди телефон olx", "подтвердить телефон олх",
                   "подтверждение телефона олх", "опубликуй это объявление",
                   "опубликуй объявление на олх", "публикуй на олх", "создай на олх",
                   "выложи на олх",
                   "удали объявление", "удалить объявление", "сними объявление",
                   "отредактируй объявление", "редактируй объявление", "измени объявление",
                   "обнови объявление", "мои объявления", "список объявлений")
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

    # ---- Instagram комментарии ----
    if any(w in t for w in ("комментари", "коментар", "отзывы под постом", "ответь на комментарий",
                            "ответь в комментар")):
        m_code = re.search(r"/p/([A-Za-z0-9_-]+)|пост\s*([A-Za-z0-9_-]{6,})", text)
        code = (m_code.group(1) or m_code.group(2)) if m_code else None
        if not code:
            api.send_message(chat_id,
                             "💬 <b>Комментарии</b>: пришлите ссылку на пост, например\n"
                             "«покажи комментарии к /p/CODE/»\n"
                             "или «ответь на комментарий в /p/CODE/: текст»")
            return True
        if any(w in t for w in ("ответь на комментарий", "ответь в комментар")):
            m_body = re.search(r":\s*(.+)$", text, re.IGNORECASE)
            body = m_body.group(1).strip() if m_body else ""
            if not body:
                api.send_message(chat_id, "💬 Напишите текст ответа после двоеточия.")
                return True
            _pending_confirm[chat_id] = {"kind": "ig_comment_reply",
                                         "data": {"code": code, "text": body}}
            api.send_message(chat_id,
                             f"💬 Ответить на комментарий к <code>{code}</code>:\n"
                             f"«{body[:150]}»\n\nОтправить? «да» / «нет»")
            return True
        api.send_message(chat_id, "⏳ Читаю комментарии…")
        data = _run_account_control(["instagram", "comments", code, "--limit", "10"])
        if data.get("status") == "ok":
            com = data.get("comments") or []
            if not com:
                api.send_message(chat_id, f"💬 У поста <code>{code}</code> комментариев нет.")
            else:
                txt = f"💬 <b>Комментарии к /p/{code}/</b>:\n" + "\n".join(
                    f"• {_esc_tg(c.get('text', ''))[:120]}" for c in com[:10])
                api.send_message(chat_id, txt)
        else:
            api.send_message(chat_id, f"❌ {data.get('error', '?')}")
        return True

    # ---- Шаблоны ответов клиентам ----
    if any(w in t for w in ("шаблон", "ответь клиенту", "быстрый ответ", "шаблоны")):
        if "добавь шаблон" in t or "сохрани шаблон" in t or "новый шаблон" in t:
            m = re.search(r"(?:добавь|сохрани|новый)\s+шаблон\s+([^:]+):\s*(.+)", text, re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                body = m.group(2).strip()
                tpl = _load_templates()
                tpl[name] = body
                _save_templates(tpl)
                api.send_message(chat_id, f"📝 Шаблон <b>{name}</b> сохранён: «{body[:80]}»")
            else:
                api.send_message(chat_id, "📝 Формат: «добавь шаблон гарантия: Здравствуйте! Да, гарантия 14 дней»")
            return True
        tpl = _load_templates()
        if "шаблоны" in t and not tpl:
            api.send_message(chat_id, "📝 Шаблонов пока нет. «добавь шаблон &lt;имя&gt;: &lt;текст&gt;»")
            return True
        # «ответь клиенту <шаблон>» — вставить шаблон в ответ
        m_use = re.search(r"(?:ответь клиенту|по шаблону|используй шаблон)\s*[\"«']?([\w\s-]+)[\"»']?", text, re.IGNORECASE)
        if m_use:
            name = m_use.group(1).strip().lower()
            found = None
            for k, v in tpl.items():
                if k.lower() == name:
                    found = v
                    break
            if not found:
                # частичное совпадение
                for k, v in tpl.items():
                    if name in k.lower() or k.lower() in name:
                        found = v
                        break
            if found:
                api.send_message(chat_id, f"📝 Шаблон <b>{name}</b>:\n«{found}»\n\n"
                                          f"Куда отправить? «отправь клиенту в директ …» или укажите канал.")
            else:
                api.send_message(chat_id, "📝 Такого шаблона нет. Доступны: " + ", ".join(tpl.keys()))
            return True
        if tpl:
            api.send_message(chat_id, "📝 <b>Шаблоны:</b>\n" + "\n".join(
                f"• <b>{_esc_tg(k)}</b>: {_esc_tg(v)[:60]}" for k, v in tpl.items()) +
                "\n\n«ответь клиенту <имя шаблона>» — показать текст")
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
    if any(w in t for w in ("вайбер", "вибер", "viber")) and not any(
            w in t for w in ("инбокс", "inbox", "все сообщения", "всё в одном", "сводка сообщений")):
        if "чернов" in t or "draft" in t:
            try:
                from viber_drafts import ViberDraftStore
                drafts = ViberDraftStore(PROJECT_ROOT).pending(12)
                if not drafts:
                    api.send_message(chat_id, "💜 Ожидающих Viber-черновиков нет.")
                else:
                    lines = ["💜 <b>Черновики Viber:</b>"]
                    for draft in drafts:
                        lines.append(f"• <b>{_esc_tg(draft.get('contact'))}</b>: «{_esc_tg(str(draft.get('text') or '')[:150])}»")
                    lines.append("\nДля отправки используйте кнопку под уведомлением-черновиком.")
                    api.send_message(chat_id, "\n".join(lines)[:3900])
            except Exception as exc:
                api.send_message(chat_id, f"⚠️ Не удалось прочитать черновики Viber: {_esc_tg(str(exc))[:180]}")
            return True
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
                                 "💬 <b>Viber</b>: напишите «напиши в вайбер &lt;имя&gt;: &lt;текст&gt;»")
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

    # ---- Signal (десктоп) ----
    if any(w in t for w in ("signal", "сигнал")) and not any(
            w in t for w in ("инбокс", "inbox", "все сообщения", "всё в одном", "сводка сообщений")):
        if "чернов" in t or "draft" in t:
            try:
                from signal_drafts import SignalDraftStore
                drafts = SignalDraftStore(PROJECT_ROOT).pending(12)
                if not drafts:
                    api.send_message(chat_id, "🔒 Ожидающих Signal-черновиков нет.")
                else:
                    lines = ["🔒 <b>Черновики Signal:</b>"]
                    for draft in drafts:
                        lines.append(f"• <b>{_esc_tg(draft.get('contact'))}</b>: «{_esc_tg(str(draft.get('text') or '')[:150])}»")
                    lines.append("\nДля отправки используйте кнопку под уведомлением-черновиком.")
                    api.send_message(chat_id, "\n".join(lines)[:3900])
            except Exception as exc:
                api.send_message(chat_id, f"⚠️ Не удалось прочитать черновики Signal: {_esc_tg(str(exc))[:180]}")
            return True
        send_word = any(w in t for w in ("напиши", "отправь", "написать", "ответь"))
        read_word = any(w in t for w in ("прочитай", "покажи", "что в", "последние"))
        if send_word:
            m = re.search(r":\s*(.+)$", text, re.IGNORECASE)
            body = m.group(1).strip() if m else ""
            target = re.sub(r"^(напиши|отправь|написать|ответь)(\s+(в|в\s+signal|signal|в\s+сигнал|сигнал))?\s+", "",
                            text, flags=re.IGNORECASE)
            target = re.sub(r"^(в|signal|сигнал)\s+", "", target, flags=re.IGNORECASE)
            target = target.split(":", 1)[0].strip(" ,.;:—–")
            if not target or not body:
                api.send_message(chat_id,
                                 "🔒 <b>Signal</b>: напишите «напиши в Signal &lt;имя&gt;: &lt;текст&gt;»")
                return True
            _pending_confirm[chat_id] = {"kind": "signal_send",
                                         "data": {"chat": target, "text": body}}
            api.send_message(chat_id,
                             f"🔒 Отправить <b>{target}</b> в Signal:\n«{body[:200]}»\n\n«да» / «нет»")
            return True
        if read_word:
            m = re.search(r"(?:signal|сигнал)[\s,:—–]*([\w\sА-Яа-яЁёІіЇїЄє'’.-]{2,30}?)(?:[.!?]|$)", text, re.IGNORECASE)
            chat = m.group(1).strip() if m else ""
            api.send_message(chat_id, "⏳ Открываю Signal…")
            data = _run_account_control(["signal", "read", chat or "Signal", "--limit", "12"])
            if data.get("status") == "ok":
                msgs = data.get("messages") or []
                if not msgs:
                    api.send_message(chat_id, "🔒 В чате нет распознанных сообщений (или пусто).")
                else:
                    api.send_message(chat_id, "🔒 <b>Signal</b>:\n" + "\n".join(
                        f"• {_esc_tg(x.get('text', ''))}" for x in msgs[-12:]))
            else:
                api.send_message(chat_id, f"❌ {data.get('error', '?')}")
            return True
        api.send_message(chat_id, "⏳ Читаю чаты Signal…")
        data = _run_account_control(["signal", "chats"])
        if data.get("status") == "ok":
            chats = data.get("chats") or []
            if chats:
                api.send_message(chat_id, "🔒 <b>Чаты Signal</b>:\n" + "\n".join(
                    f"• {_esc_tg(c.get('name'))}" for c in chats[:20]))
            else:
                api.send_message(chat_id,
                                 "🔒 Не нашёл чаты Signal (возможно, нужен повторный QR-вход).")
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
                                 "💬 <b>Messenger</b>: напишите «напиши в мессенджер &lt;имя&gt;: &lt;текст&gt;»")
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

    # ---- Расписание инбокса ----
    if re.match(r"^(присылай|пришли|включи|отключи|выключи|убери)\s+инбокс", t) or \
       re.match(r"^(включи|отключи)\s+расписание\s+инбокса", t):
        _inbox_schedule_cmd(api, chat_id, text)
        return True

    # ---- Экспорт данных ----
    if any(w in t for w in ("экспортируй", "выгрузи", "экспорт", "в excel", "в эксель",
                            "выгрузить в файл")):
        import subprocess as _sp
        if "почт" in t or "gmail" in t or "письм" in t:
            api.send_message(chat_id, "⏳ Экспортирую почту в Excel…")
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_export.py"), "gmail", "50"],
                        capture_output=True, text=True, timeout=90, cwd=str(PROJECT_ROOT))
        elif "контакт" in t:
            api.send_message(chat_id, "⏳ Экспортирую контакты в Excel…")
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_export.py"), "contacts", "200"],
                        capture_output=True, text=True, timeout=170, cwd=str(PROJECT_ROOT))
        elif "финанс" in t or "продаж" in t or "склад" in t or "детал" in t:
            what = "finance" if "финанс" in t or "продаж" in t else "inventory"
            api.send_message(chat_id, f"⏳ Экспортирую {'финансы' if what == 'finance' else 'склад'} в CSV (для Google Таблиц)…")
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_export.py"), what],
                        capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
        else:  # olx
            q = re.sub(r"(экспортируй|выгрузи|экспорт|объявления)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
            q = q.replace("олх", "").replace("olx", "").strip(" ,.;:—–")
            api.send_message(chat_id, f"⏳ Экспортирую объявления OLX{' «' + q + '»' if q else ''} в Excel…")
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_export.py"), "olx"] + ([q] if q else []),
                        capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT))
        try:
            out = (r.stdout or "").strip()
            start = out.find("{")
            res = json.loads(out[start:]) if start >= 0 else {"error": out[-200:]}
        except Exception:
            res = {"error": (r.stderr or "?")[-200:]}
        if res.get("status") == "ok" and res.get("file") and os.path.exists(res["file"]):
            try:
                api.send_document(chat_id, res["file"], caption=f"📑 Экспорт ({res.get('rows', '?')} строк)")
            except Exception as e:
                api.send_message(chat_id, f"✅ Файл готов: {res['file']} (не смог отправить: {e})")
        else:
            api.send_message(chat_id, f"❌ Экспорт не удался: {res.get('error', '?')}")
        return True

    # ---- Распознавание фото запчасти ----
    if any(w in t for w in ("распознай деталь", "что за деталь", "определи деталь",
                            "оцени деталь", "узнай деталь", "деталь по фото")):
        photo = _last_photo.get(chat_id)
        if not photo:
            api.send_message(chat_id, "📷 Сначала пришлите фото детали, потом «распознай деталь»")
            return True
        api.send_message(chat_id, "🤖 Распознаю деталь по фото (Gemini vision)… ~30 сек")
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_photo_recognition.py"), photo],
                    capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") == "ok":
            txt = (f"🔍 <b>Распознано:</b>\n"
                   f"🔩 Деталь: <b>{_esc_tg(res.get('part', '?'))}</b>\n"
                   f"📋 Состояние: {_esc_tg(res.get('condition') or '—')}\n"
                   f"💰 Цена: {res.get('price') or '?'} грн\n"
                   f"🚗 Совместимость: {_esc_tg(res.get('compatible') or '—')}\n"
                   f"📝 {_esc_tg(res.get('notes') or '')}\n\n"
                   f"Добавить на склад? «добавь деталь {res.get('part', '')}, 1 шт»\n"
                   f"Или «создай объявление: {res.get('part', '')}»")
            api.send_message(chat_id, txt[:3900])
        else:
            api.send_message(chat_id, f"❌ {res.get('error', 'Не удалось распознать')}")
        return True

    # ---- Фото детали → черновик объявления ----
    if any(w in t for w in ("сделай объявление из фото", "объявление по фото", "фото в объявление",
                            "выложи по фото", "деталь по фото")):
        photo = _last_photo.get(chat_id)
        if not photo:
            api.send_message(chat_id, "📷 Сначала пришлите фото детали, потом «сделай объявление из фото»")
            return True
        api.send_message(chat_id, "📷 Отлично, фото получил! Опишите деталь одним сообщением, например:\n"
                                  "«фара BMW X5 ксенон 2003, цена 2000»\n— и я сгенерирую объявление.")
        _photo_pending[chat_id] = True
        return True
    if chat_id in _photo_pending and _photo_pending[chat_id]:
        # это описание детали после фото
        _photo_pending[chat_id] = False
        photo = _last_photo.get(chat_id, "")
        part = text.strip()
        import subprocess as _sp
        api.send_message(chat_id, f"⏳ Генерирую объявление по фото: «{part}»…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_ad_gen.py"), "gen", part],
                    capture_output=True, text=True, timeout=90, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-150:]}
        if res.get("status") == "ok":
            txt = (f"📝 <b>Объявление (по фото):</b>\n"
                   f"Заголовок: <b>{_esc_tg(res.get('title', ''))}</b>\n"
                   f"Цена: {res.get('price', '?')} грн\n\n"
                   f"Описание:\n{_esc_tg(res.get('description', ''))}\n\n"
                   f"Фото приложу при публикации на OLX (после подтверждения телефона).")
            api.send_message(chat_id, txt)
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    # ---- Генератор объявлений OLX ----
    if any(w in t for w in ("создай объявление", "создай объявлени", "новое объявление на олх",
                            "создай объявления", "создай объявления из списка",
                            "напиши объявление")):
        import subprocess as _sp
        if "из списка" in t or "массов" in t:
            body = re.sub(r"^(создай объявления из списка|создай массово)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
            if not body:
                api.send_message(chat_id, "📋 «создай объявления из списка: деталь1; деталь2; деталь3»")
                return True
            api.send_message(chat_id, "⏳ Генерирую объявления (по одному, быстро)…")
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_ad_gen.py"),
                         "gen_many", body], capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT))
            try:
                res = json.loads((r.stdout or "").strip().split("\n")[-1])
            except Exception:
                res = {"status": "error", "error": (r.stderr or "?")[-150:]}
            if res.get("status") == "ok":
                ads = res.get("ads") or []
                lines = ["📋 <b>Сгенерированные объявления:</b>"]
                for i, a in enumerate(ads, 1):
                    lines.append(f"{i}. <b>{_esc_tg(a.get('title', ''))}</b> — {a.get('price', '?')} грн")
                lines.append("\nСоздать на OLX: «создай объявление: <деталь>» (нужно подтвердить телефон)")
                api.send_message(chat_id, "\n".join(lines)[:3900])
            else:
                api.send_message(chat_id, f"❌ {res.get('error', '?')}")
            return True
        # одно объявление
        part = re.sub(r"^(создай объявление|создай новое объявление|напиши объявление)\s*(на олх)?\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
        part = part.replace("олх", "").replace("olx", "").strip(" ,.;:—–")
        if not part:
            api.send_message(chat_id, "📝 «создай объявление: фара BMW X5 2000 грн»")
            return True
        api.send_message(chat_id, "⏳ Генерирую объявление через AI…")
        _last_gen_ad[chat_id] = part
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_ad_gen.py"), "gen", part],
                    capture_output=True, text=True, timeout=90, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-150:]}
        if res.get("status") == "ok":
            txt = (f"📝 <b>Сгенерировано объявление:</b>\n"
                   f"Заголовок: <b>{_esc_tg(res.get('title', ''))}</b>\n"
                   f"Цена: {res.get('price', '?')} грн\n\n"
                   f"Описание:\n{_esc_tg(res.get('description', ''))}\n\n"
                   f"Публиковать на OLX? Напишите «опубликуй это объявление» — "
                   f"но сначала нужно подтвердить телефон в профиле (через VNC).")
            api.send_message(chat_id, txt)
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    # ---- Мониторинг цен OLX ----
    if any(w in t for w in ("следи за ценой", "мониторинг цен", "цена на олх", "снизил",
                            "отпишись от цены", "цены на олх", "мои цены")):
        subs_file = PROJECT_ROOT / "data" / "olx_price_subs.json"
        try:
            subs = json.loads(subs_file.read_text(encoding="utf-8"))
        except Exception:
            subs = {}
        if "отпишись от цены" in t or "убери цену" in t:
            q = re.sub(r"(отпишись от цены|убери цену)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
            cur = subs.get(str(chat_id), [])
            cur = [e for e in cur if e.get("query", "").lower() != q.lower()]
            subs[str(chat_id)] = cur
            subs_file.parent.mkdir(parents=True, exist_ok=True)
            subs_file.write_text(json.dumps(subs, ensure_ascii=False, indent=2), encoding="utf-8")
            api.send_message(chat_id, f"📉 Отписался от цены «{q}».")
            return True
        if "мои цены" in t or ("цены" in t and not any(w in t for w in ("следи", "монитор"))):
            cur = subs.get(str(chat_id), [])
            if not cur:
                api.send_message(chat_id, "📉 Нет подписок на цены. «следи за ценой &lt;запрос&gt;»")
            else:
                api.send_message(chat_id, "📉 <b>Подписки на цены:</b>\n" + "\n".join(
                    f"• {_esc_tg(e.get('query'))} — мин {e.get('last_min') or '?'} грн" for e in cur))
            return True
        # добавить подписку
        q = re.sub(r"(следи за ценой|мониторинг цены|цена на олх)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
        if not q:
            api.send_message(chat_id, "📉 «следи за ценой &lt;запрос&gt;», например: следи за ценой фары BMW X5")
            return True
        cur = subs.get(str(chat_id), [])
        if any(e.get("query", "").lower() == q.lower() for e in cur):
            api.send_message(chat_id, f"📉 Уже слежу за «{q}».")
            return True
        # проверить текущую минимальную цену
        import subprocess as _sp
        try:
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_price_alerts.py"),
                         "--probe", q], capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
        except Exception:
            r = None
        cur_min = None
        if r and r.stdout:
            try:
                cur_min = float(r.stdout.strip())
            except Exception:
                pass
        cur.append({"query": q, "last_min": cur_min,
                    "since": datetime.now().strftime("%Y-%m-%d %H:%M")})
        subs[str(chat_id)] = cur
        subs_file.parent.mkdir(parents=True, exist_ok=True)
        subs_file.write_text(json.dumps(subs, ensure_ascii=False, indent=2), encoding="utf-8")
        api.send_message(chat_id,
                         f"📉 Слежу за ценой «{q}»" +
                         (f". Сейчас минимум: {cur_min} грн" if cur_min else "") +
                         ".\nУведомлю при снижении >5%. «мои цены» — список, «отпишись от цены &lt;запрос&gt;» — убрать.")
        return True

    # ---- Единый инбокс ----
    if any(w in t for w in ("инбокс", "inbox", "все сообщения", "всё в одном",
                            "сводка сообщений", "где что новое", "проверь всё")):
        filters = _parse_inbox_filters(text)
        api.send_message(chat_id, "⏳ Собираю инбокс (почта, TG, IG, Messenger, Viber, Signal, OLX)… ~1 мин")
        items, summary = _collect_inbox(filters)
        if not items:
            api.send_message(chat_id, "📭 Везде пусто (или не удалось собрать).")
            return True
        _last_inbox[chat_id] = items
        txt = _format_inbox(items, filters)
        # умное резюме (если запрошено «сводка» или всегда кратко)
        if "сводк" in t or "резюме" in t or "кратко" in t or "умн" in t:
            api.send_message(chat_id, "🧠 Составляю умное резюме…")
            api.send_message(chat_id, _inbox_summarize(items)[:3900])
        else:
            api.send_message(chat_id, txt, reply_markup=_inbox_keyboard(items))
            api.send_message(chat_id,
                             "ℹ️ «сводка» — умное резюме · «ответь на N: …» — ответить\n"
                             "«озвучь инбокс» — голосом · «инбокс только непрочитанное» — фильтр")
        return True

    # ---- Ответы из инбокса ----
    m_reply = re.match(r"^(ответь|reply|отв[её]ть)\s+(?:на\s+)?#?(\d+)\s*:?\s*(.+)$", text, re.IGNORECASE)
    if m_reply and chat_id in _last_inbox:
        idx = int(m_reply.group(2))
        body = m_reply.group(3).strip()
        if 1 <= idx <= len(_last_inbox[chat_id]):
            _inbox_reply(api, chat_id, _last_inbox[chat_id][idx - 1], body)
            return True
        api.send_message(chat_id, f"❌ Нет пункта №{idx} в последнем инбоксе.")
        return True

    # ---- Озвучить инбокс ----
    if any(w in t for w in ("озвучь инбокс", "озвучь всё", "голосом инбокс", "прочитай инбокс вслух")):
        api.send_message(chat_id, "⏳ Собираю и озвучиваю…")
        items, summary = _collect_inbox({})
        if not items:
            api.send_message(chat_id, "📭 Везде пусто.")
            return True
        _last_inbox[chat_id] = items
        _inbox_voice(api, chat_id, items)
        return True

    # ---- Поиск по всем каналам ----
    m_glob = re.match(r"^(найди во всех|ищи везде|найди везде|поиск по всем)\s*(?:чатах|сообщениях|каналах)?\s*:?\s*(.+)$", text, re.IGNORECASE)
    if m_glob:
        q = m_glob.group(2).strip()
        if not q:
            api.send_message(chat_id, "🔍 «найди во всех чатах &lt;запрос&gt;»")
            return True
        api.send_message(chat_id, f"🔍 Ищу «{q}» по почте, TG, IG, Messenger… (может занять 1-2 мин)")
        _inbox_search(api, chat_id, q)
        return True

    # ---- Отметить всё прочитанным ----
    if any(w in t for w in ("отметь всё прочитанным", "отметить все прочитанными", "всё прочитано",
                            "отметь прочитанным")):
        _inbox_mark_read(api, chat_id)
        return True

    # ---- SMS-уведомления (вкл/выкл) ----
    if any(w in t for w in ("включи смс-уведомления", "включи уведомления о смс", "смс-алерты вкл",
                            "включи смс уведомления", "смс уведомления вкл")):
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_sms_alerts.py"), "--on"],
                    capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
        api.send_message(chat_id, "🔔 SMS-уведомления <b>включены</b>: новые важные SMS (коды, OLX, Новая Почта, банки) будут приходить сюда.")
        return True
    if any(w in t for w in ("выключи смс-уведомления", "отключи уведомления о смс", "смс-алерты выкл",
                            "выключи смс уведомления", "смс уведомления выкл")):
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_sms_alerts.py"), "--off"],
                    capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
        api.send_message(chat_id, "🔕 SMS-уведомления <b>выключены</b>. «мои смс» — по-прежнему можно читать вручную.")
        return True
    if any(w in t for w in ("статус смс-уведомлений", "смс-уведомления статус", "работают ли смс-уведомления")):
        try:
            st = json.loads((PROJECT_ROOT / "data" / "sms_alerts_state.json").read_text(encoding="utf-8"))
            api.send_message(chat_id,
                             f"🔔 SMS-уведомления: {'<b>включены</b>' if st.get('enabled', True) else '<b>выключены</b>'}\n"
                             f"Отправлено уведомлений: {st.get('notified', 0)}\n"
                             f"Проверка: {st.get('last_check', '—')[:16]}")
        except Exception:
            api.send_message(chat_id, "🔔 SMS-уведомления ещё не инициализированы (запустится автоматически).")
        return True

    # ---- SMS (Google Messages for Web, телефон +380959052288) ----
    if any(w in t for w in ("мои смс", "последние смс", "последняя смс", "проверь смс",
                            "смс на телефон", "что пришло по смс", "мои смски")):
        import subprocess as _sp
        api.send_message(chat_id, "⏳ Читаю SMS с телефона…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_account_control.py"),
                     "messages", "latest", "--limit", "10"],
                    capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") == "ok":
            sms = res.get("sms") or []
            if not sms:
                api.send_message(chat_id, "📭 В SMS пусто.")
            else:
                lines = ["💬 <b>Последние SMS:</b>"]
                for s in sms[:10]:
                    code = f" · 🔑 <b>{s.get('code')}</b>" if s.get("code") else ""
                    lines.append(f"• <b>{_esc_tg(s.get('sender'))}</b>{code}: {_esc_tg(s.get('text', ''))[:90]}")
                api.send_message(chat_id, "\n".join(lines)[:3900])
        else:
            api.send_message(chat_id, f"❌ {res.get('error', 'Не удалось прочитать SMS')}")
        return True

    m_code = re.match(r"^(?:найди код из смс|код из смс|код подтверждения|какой код|код от)\s*(?:от|с)?\s*:?\s*(.*)$",
                      text, re.IGNORECASE)
    if m_code and ("код" in text.lower() or "смс" in text.lower()):
        sender = m_code.group(1).strip()
        import subprocess as _sp
        api.send_message(chat_id, f"🔑 Ищу код в SMS{f' от «{sender}»' if sender else ''}…")
        args = ["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_account_control.py"),
                "messages", "code"]
        if sender:
            args.append(sender)
        r = _sp.run(args, capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") == "ok":
            api.send_message(chat_id,
                             f"🔑 <b>Код: {res.get('code')}</b>\n"
                             f"От: {_esc_tg(res.get('sender'))}\n{_esc_tg(res.get('message'))[:150]}")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', 'Код не найден')}")
        return True

    m_msgs_read = re.match(r"^(?:прочитай смс от|переписка|смс от|покажи переписку)\s+([^\n]{1,60})$",
                           text, re.IGNORECASE)
    if m_msgs_read:
        contact = m_msgs_read.group(1).strip().strip("«»\"'")
        import subprocess as _sp
        api.send_message(chat_id, f"💬 Открываю переписку с «{contact}»…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_account_control.py"),
                     "messages", "read", contact, "--limit", "12"],
                    capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") == "ok":
            msgs = res.get("messages") or []
            lines = [f"💬 <b>{_esc_tg(contact)}</b>:"]
            for m in msgs[:12]:
                lines.append(f"• {_esc_tg(m.get('text', ''))[:160]}")
            api.send_message(chat_id, "\n".join(lines)[:3900])
        else:
            api.send_message(chat_id, f"❌ {res.get('error', 'Не удалось прочитать переписку')}")
        return True

    m_msgs_send = re.match(r"^(?:отправь смс|напиши смс|отправь sms)\s+([^\n:]+)\s*:\s*(.+)$",
                           text, re.IGNORECASE)
    if m_msgs_send:
        contact = m_msgs_send.group(1).strip().strip("«»\"'")
        body = m_msgs_send.group(2).strip()
        _pending_confirm[chat_id] = {"kind": "messages_send",
                                     "data": {"to": contact, "text": body}}
        api.send_message(chat_id,
                         f"📨 Отправить SMS на «{_esc_tg(contact)}»:\n{_esc_tg(body)[:200]}\n\n«да» / «нет»")
        return True

    if any(w in t for w in ("покажи смс", "скрин смс", "скриншот смс")):
        import subprocess as _sp
        api.send_message(chat_id, "⏳ Делаю скриншот Messages…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_account_control.py"),
                     "messages", "screenshot"], capture_output=True, text=True,
                    timeout=120, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": "?"}
        if res.get("status") == "ok" and res.get("screenshot"):
            _acct_send_result(api, chat_id, {"status": "ok", "text": "💬 Экран Messages",
                                             "screenshot": res["screenshot"],
                                             "caption": "💬 Messages"}, "")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', 'Не удалось сделать скриншот')}")
        return True

    # ---- Массовая выгрузка склада на OLX ----
    if any(w in t for w in ("выложи весь склад", "выгрузи склад на олх", "опубликуй весь склад",
                            "склад на олх", "выложи склад", "выгрузи склад",
                            "все объявления со склада", "весь склад на олх", "склад на olx")):
        import subprocess as _sp
        api.send_message(chat_id, "⏳ Читаю склад и генерирую объявления…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_ad_gen.py"), "export_sklad"],
                    capture_output=True, text=True, timeout=180, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") != "ok":
            api.send_message(chat_id, f"❌ {res.get('error', 'Не удалось прочитать склад')}")
            return True
        results = res.get("results") or []
        if not results:
            api.send_message(chat_id, "📦 Склад пуст — добавьте детали: «добавь деталь: …»")
            return True
        lines = ["📦 <b>Склад → OLX:</b>"]
        for x in results[:20]:
            st = "✅" if x.get("status") == "ok" else "❌"
            lines.append(f"{st} {_esc_tg(x.get('name'))} — {x.get('price_gen') or x.get('price')} грн")
        lines.append("\n" + (f"Всего: {res.get('total')} позиций. Опубликовать на OLX?" if res.get('err') == 0
                             else f"Готово {res.get('ok')} из {res.get('total')}. Опубликовать готовые?"))
        _pending_confirm[chat_id] = {"kind": "olx_bulk", "data": {"total": res.get("total")}}
        api.send_message(chat_id, "\n".join(lines)[:3900])
        return True

    # ---- Клиенты и отправки Новой Почты ----
    m_client = re.match(r"^(?:добавь клиента|запиши клиента)\s*:\s*(.+)$", text, re.IGNORECASE)
    if m_client:
        parts = [p.strip() for p in re.split(r"[,;]|, ", m_client.group(1)) if p.strip()]
        if len(parts) < 2:
            api.send_message(chat_id, "📇 Формат: «добавь клиента: ФИО, телефон, город, отделение»")
            return True
        name = parts[0]
        phone = parts[1]
        city = parts[2] if len(parts) > 2 else ""
        wh = parts[3] if len(parts) > 3 else ""
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_shipments.py"),
                     "add_client", name, phone, city, wh], capture_output=True, text=True,
                    timeout=20, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": "?"}
        if res.get("status") == "ok":
            c = res.get("client", {})
            api.send_message(chat_id, f"📇 <b>{c.get('name')}</b> — {c.get('phone')} · {c.get('city')} {c.get('warehouse')} · {res.get('msg')}")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    if any(w in t for w in ("мои клиенты", "список клиентов", "клиенты")):
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_shipments.py"), "clients"],
                    capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": "?"}
        if res.get("status") == "ok" and res.get("clients"):
            lines = ["📇 <b>Клиенты:</b>"]
            for c in res["clients"][:15]:
                lines.append(f"• <b>{_esc_tg(c.get('name'))}</b> — {c.get('phone')} · {c.get('city')} {c.get('warehouse')}")
            api.send_message(chat_id, "\n".join(lines)[:3900])
        else:
            api.send_message(chat_id, "📇 Клиентов пока нет. «добавь клиента: ФИО, телефон, город, отделение»")
        return True

    m_ship = re.match(r"^(?:запиши отправку|отправить|отправка)\s*:\s*(.+)$", text, re.IGNORECASE)
    if m_ship:
        # «деталь» -> «получатель» (клиент по имени) или «деталь»: ФИО, телефон, город, отделение
        spec = m_ship.group(1).strip()
        parts = [p.strip() for p in spec.split(",") if p.strip()]
        detail = parts[0]
        if len(parts) >= 3 and "@" in "".join(parts[1:2]):
            pass
        import subprocess as _sp
        if len(parts) >= 3:
            # деталь, ФИО, телефон[, город, отделение]
            cmd = ["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_shipments.py"),
                   "ship", detail, parts[1], parts[2],
                   parts[3] if len(parts) > 3 else "",
                   parts[4] if len(parts) > 4 else ""]
        else:
            # деталь -> клиент (имя из базы)
            client_ref = parts[1] if len(parts) > 1 else ""
            cmd = ["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_shipments.py"),
                   "ship", detail, client_ref]
        r = _sp.run(cmd, capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": "?"}
        if res.get("status") == "ok":
            s = res.get("shipment", {})
            api.send_message(chat_id,
                             f"📦 <b>Отправка:</b> {_esc_tg(s.get('detail'))} → {_esc_tg(s.get('recipient'))}\n"
                             f"📞 {s.get('phone')} · {s.get('city')} {s.get('warehouse')}\n"
                             f"Статус: {s.get('status')}")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}\nСначала «добавь клиента: ФИО, телефон, город, отделение»")
        return True

    if any(w in t for w in ("мои отправки", "отправки", "заказы на отправку")):
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_shipments.py"), "ships"],
                    capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": "?"}
        if res.get("status") == "ok" and res.get("shipments"):
            lines = ["📦 <b>Отправки:</b>"]
            for s in res["shipments"][:12]:
                lines.append(f"• {_esc_tg(s.get('detail'))} → {_esc_tg(s.get('recipient'))} ({s.get('status')})")
            api.send_message(chat_id, "\n".join(lines)[:3900])
        else:
            api.send_message(chat_id, "📦 Отправок пока нет.")
        return True

    # ---- Отчёт по OLX ----
    if any(w in t for w in ("отчёт по олх", "отчет по олх", "отчёт олх", "сводка олх",
                            "статистика олх", "сколько объявлений на олх", "сводка по олх")):
        import subprocess as _sp
        api.send_message(chat_id, "⏳ Собираю отчёт по OLX…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_report.py")],
                    capture_output=True, text=True, timeout=150, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        from run_olx_report import format_report
        api.send_message(chat_id, format_report(res)[:3900])
        return True

    # ---- Новая Почта: создание ТТН ----
    m_ttn = re.match(r"^(?:создай ттн|создать ттн|накладная|создай накладную)\s*:?\s*(.+)$",
                     text, re.IGNORECASE)
    if m_ttn:
        # формат: деталь, цена, ФИО, телефон, город, отделение
        parts = [p.strip() for p in re.split(r"[,;]", m_ttn.group(1)) if p.strip()]
        if len(parts) < 6:
            api.send_message(chat_id,
                             "📦 Формат: «создай ттн: деталь, цена, ФИО, телефон, город, отделение»\n"
                             "Пример: создай ттн: фара BMW X5, 2000, Іван Петренко, 0671234567, Київ, Відділення №1")
            return True
        detail, cost, recipient, phone, city, wh = parts[:6]
        _pending_confirm[chat_id] = {"kind": "ttn_create",
                                     "data": {"detail": detail, "cost": cost,
                                              "recipient": recipient, "phone": phone,
                                              "city": city, "warehouse": wh}}
        api.send_message(chat_id,
                         f"📦 Создать ТТН Новой Почты:\n"
                         f"Деталь: <b>{_esc_tg(detail)}</b> · {cost} грн\n"
                         f"Получатель: {_esc_tg(recipient)} · {phone}\n"
                         f"{_esc_tg(city)} · {_esc_tg(wh)}\n\n«да» / «нет»")
        return True

    if any(w in t for w in ("проверь ттн", "настройки ттн", "готов ли отправитель нп",
                            "отправитель новой почты")):
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_ttn.py"), "whoami"],
                    capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": "?"}
        if res.get("status") == "ok":
            s = res.get("sender", {})
            if s.get("ready"):
                api.send_message(chat_id,
                                 f"✅ Отправитель НП готов: <b>{_esc_tg(s.get('description'))}</b>\n"
                                 f"Адрес: {_esc_tg(s.get('address') or '—')}\n"
                                 f"Можно создавать ТТН: «создай ттн: …»")
            else:
                api.send_message(chat_id,
                                 "⚠️ <b>Отправитель НП не настроен</b> в кабинете API.\n"
                                 "1. Зайдите: cabinet.novaposhta.ua\n"
                                 "2. Настройки → «Мои данные/Отправитель»\n"
                                 "3. Заполните ФИО, телефон +380959052288 и адрес отправки "
                                 "(напр. Відділення №8, Кропивницький)\n"
                                 "После этого напишите «проверь ттн» — и создание накладных заработает.")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    # ---- OLX-чат (сообщения покупателей) ----
    if any(w in t for w in ("сообщения на олх", "переписки олх", "чат олх", "сообщения в олх",
                            "переписки на олх", "чат на олх", "что пишут на олх")):
        import subprocess as _sp
        api.send_message(chat_id, "⏳ Открываю чат OLX…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_account_control.py"),
                     "olx", "chat", "list"], capture_output=True, text=True, timeout=120,
                    cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") != "ok":
            api.send_message(chat_id, f"❌ {res.get('error', 'Не удалось открыть чат')}")
            return True
        threads = res.get("threads") or []
        if not threads:
            api.send_message(chat_id, "💬 В чате OLX пока нет переписок.")
            return True
        lines = ["💬 <b>OLX-чат:</b>"]
        for x in threads[:12]:
            lines.append(f"• <b>{_esc_tg(x.get('name'))}</b>: {_esc_tg(x.get('text', ''))[:80]}")
        if res.get("unread_present"):
            lines.append("\n🔴 Есть непрочитанные!")
        lines.append("\nЧитать: «прочитай чат <имя>» · Ответить: «ответь покупателю на олх: <имя>: <текст>»")
        api.send_message(chat_id, "\n".join(lines)[:3900])
        return True

    m_chat_read = re.match(r"^(?:прочитай чат|сообщения от|переписка с|чат с)\s+([^\n]{1,50})$",
                           text, re.IGNORECASE)
    # не перехватываем чужие мессенджеры (телега, вайбер, тикток и т.п.)
    if m_chat_read and not any(x in text.lower() for x in (
            "телеграм", "телеге", "теге", "тегу", "тегу", "тг", "тикток", "tiktok",
            "вайбер", "viber", "signal", "сигнал", "вотсап", "whatsapp", "мессенджер", "messenger")):
        contact = m_chat_read.group(1).strip().strip("«»\"'")
        import subprocess as _sp
        api.send_message(chat_id, f"💬 Читаю переписку с «{contact}»…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_account_control.py"),
                     "olx", "chat", "read", contact], capture_output=True, text=True, timeout=120,
                    cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") != "ok":
            api.send_message(chat_id, f"❌ {res.get('error', 'Не удалось прочитать')}")
            return True
        msgs = res.get("messages") or []
        if not msgs:
            api.send_message(chat_id, f"💬 С «{contact}» сообщений нет.")
            return True
        lines = [f"💬 <b>{_esc_tg(contact)}</b>:"]
        for m in msgs[:15]:
            who = "👤" if not m.get("mine") else "🙋"
            lines.append(f"{who} {_esc_tg(m.get('text', ''))[:200]}")
        lines.append("\nОтветить: «ответь покупателю на олх: <имя>: <текст>»")
        api.send_message(chat_id, "\n".join(lines)[:3900])
        return True

    m_chat_reply = re.match(r"^(?:ответь покупателю на олх|ответь на олх|ответь в олх)\s*[:\-]?\s*([^:\n]{1,50})\s*:\s*(.+)$",
                            text, re.IGNORECASE)
    if m_chat_reply:
        contact = m_chat_reply.group(1).strip().strip("«»\"'")
        body = m_chat_reply.group(2).strip()
        _pending_confirm[chat_id] = {"kind": "olx_chat_reply",
                                     "data": {"to": contact, "text": body}}
        api.send_message(chat_id,
                         f"📨 Ответ покупателю «{_esc_tg(contact)}»:\n{_esc_tg(body)[:300]}\n\n«да» / «нет»")
        return True

    # ---- Поднятие/контроль объявлений OLX ----
    if any(w in t for w in ("подними объявления", "подними мои объявления", "обнови объявления",
                            "мои объявления олх", "мои объявления olx", "контроль объявлений",
                            "сколько объявлений")):
        import subprocess as _sp
        do_boost = "подними" in t or "обнови" in t or "поднять" in t
        api.send_message(chat_id, "⏳ Открываю кабинет OLX…")
        args = ["--boost"] if do_boost else []
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_boost.py")] + args,
                    capture_output=True, text=True, timeout=170, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") == "ok":
            txt = (f"🛒 <b>Объявления OLX</b>\n"
                   f"Найдено объявлений: {res.get('ads_found') or 0}\n"
                   f"Кнопок «поднять»: {res.get('refresh_buttons') or 0}")
            if res.get("boosted"):
                txt += "\n✅ Первое объявление поднято!"
            if res.get("ads_preview"):
                txt += "\n\n" + "\n".join(f"• {_esc_tg(x)}" for x in res["ads_preview"][:5])
            _acct_send_result(api, chat_id, {"status": "ok", "text": txt,
                                             "screenshot": res.get("screenshot"),
                                             "caption": "🛒 Объявления OLX"}, "")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    # ---- Удаление/редактирование объявлений OLX ----
    m_del = re.match(r"^(удали объявление|удалить объявление|удали|сними объявление|снять объявление)\s*(?:№\s*)?(\d{5,12})\b", text, re.IGNORECASE)
    if m_del:
        ad_id = m_del.group(2)
        _pending_confirm[chat_id] = {"kind": "olx_delete", "data": {"ad_id": ad_id}}
        api.send_message(chat_id, f"🗑 Удалить объявление <b>{ad_id}</b> с OLX?\n«да» / «нет»")
        return True

    m_edit = re.match(r"^(отредактируй объявление|редактируй объявление|измени объявление|обнови объявление)\s*(?:№\s*)?(\d{5,12})\b\s*:?\s*(.*)$", text, re.IGNORECASE)
    if m_edit:
        ad_id = m_edit.group(2)
        edit_spec = m_edit.group(3).strip()
        # парсим: «цена 1500», «заголовок …», «описание …»
        title = description = price = ""
        m_p = re.search(r"(?:цена|ціна)\s+(\d{2,7})", edit_spec, re.IGNORECASE)
        if m_p:
            price = m_p.group(1)
        m_t = re.search(r"(?:заголовок|название|назва)\s*[:—-]\s*(.+)", edit_spec, re.IGNORECASE)
        if m_t:
            title = m_t.group(1).strip().split(",")[0][:150]
        m_d = re.search(r"(?:описание|опис)\s*[:—-]\s*(.+)", edit_spec, re.IGNORECASE)
        if m_d:
            description = m_d.group(1).strip()
        if not (title or description or price):
            api.send_message(chat_id, "📝 Формат: «отредактируй объявление &lt;id&gt;: цена 1500, заголовок: …»\n"
                                      "или «отредактируй объявление &lt;id&gt;: описание: …»")
            return True
        _pending_confirm[chat_id] = {"kind": "olx_edit",
                                     "data": {"ad_id": ad_id, "title": title,
                                              "description": description, "price": price}}
        api.send_message(chat_id, f"📝 Отредактировать объявление <b>{ad_id}</b>:\n"
                                  f"{'Цена: ' + price + chr(10) if price else ''}"
                                  f"{'Заголовок: ' + title + chr(10) if title else ''}"
                                  f"{'Описание: ' + description[:80] if description else ''}"
                                  f"\n\n«да» / «нет»")
        return True

    if any(w in t for w in ("мои объявления", "мои объявлени", "список объявлений",
                            "какие у меня объявления")):
        import subprocess as _sp
        api.send_message(chat_id, "⏳ Загружаю мои объявления…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_account_control.py"),
                     "olx", "my_ads"], capture_output=True, text=True, timeout=90, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": "?"}
        if res.get("status") == "ok":
            if res.get("ads"):
                lines = ["🛒 <b>Мои объявления OLX:</b>"]
                for a in res["ads"][:15]:
                    lines.append(f"• <b>{_esc_tg(a.get('title', '?'))}</b> — {a.get('price', '?')} грн · id {a.get('id')}")
                lines.append("\nУдалить: «удали объявление &lt;id&gt;» · Редактировать: «отредактируй объявление &lt;id&gt;: цена 1500»")
                api.send_message(chat_id, "\n".join(lines)[:3900])
            else:
                api.send_message(chat_id, "🛒 Сейчас опубликованных объявлений нет.\n"
                                          "Создать: «создай объявление: <деталь>» → «опубликуй это объявление»\n"
                                          "id появится в журнале после публикации.")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', 'Не удалось получить список объявлений')}")
        return True

    # ---- Подтверждение телефона OLX + публикация ----
    if any(w in t for w in ("подтверди телефон олх", "подтверди телефон olx", "подтвердить телефон олх",
                            "подтверждение телефона олх")):
        api.send_message(chat_id,
                         "📱 <b>Подтверждение телефона OLX</b>\n\n"
                         "Это одноразовое действие (как вход в соцсети):\n"
                         "1. Я открою VNC и страницу подтверждения\n"
                         "2. Подключитесь: <code>167.233.95.7:5901</code> (пароль <code>aios1234</code>)\n"
                         "3. Введите номер телефона, нажмите «Отримати код», введите код из Viber/SMS\n"
                         "4. Готово — напишите мне, я закрою VNC, и публикация объявлений заработает.\n\n"
                         "Открываю VNC сейчас…")
        import subprocess as _sp
        try:
            _sp.run(["ufw", "allow", "5901/tcp"], capture_output=True, timeout=15)
            _sp.run(["bash", "-c", "pkill -9 -f '[X]vnc :1' 2>/dev/null; sleep 1; "
                                    "vncserver :1 -geometry 1920x1080 -depth 24 -localhost no >/dev/null 2>&1"],
                    capture_output=True, timeout=60)
            _sp.run(["bash", "-c",
                     "export DISPLAY=:1; rm -f /root/AIOS/data/chrome_twin/default/Singleton*; "
                     "nohup /usr/bin/google-chrome-stable --no-sandbox "
                     "--user-data-dir=/root/AIOS/data/chrome_twin/default "
                     "--no-first-run --no-default-browser-check --disable-infobars "
                     "\"https://www.olx.ua/d/uk/adding/\" > /tmp/olx_confirm.log 2>&1 &"],
                    capture_output=True, timeout=30)
            api.send_message(chat_id, "✅ VNC открыт. Жду вас: <code>167.233.95.7:5901</code>, пароль <code>aios1234</code>")
        except Exception as e:
            api.send_message(chat_id, f"⚠️ Не смог открыть VNC: {e}")
        return True

    if any(w in t for w in ("опубликуй это объявление", "опубликуй объявление на олх",
                            "публикуй на олх", "создай на олх", "выложи на олх",
                            "опубликуй объявление", "опубликовать объявление",
                            "выложи объявление", "публикуй объявление", "опубликуй на олх",
                            "публикуй это объявление", "выложи это объявление")):
        # берём деталь из текста или из последнего сгенерированного
        m_d = re.search(r"(?:объявление|на олх|на олх:)\s*[:—-]\s*(.+)$", text, re.IGNORECASE)
        part = m_d.group(1).strip() if m_d else ""
        # «опубликуй это объявление» без детали — берём из памяти
        if not part and "это объявление" in t:
            part = _last_gen_ad.get(chat_id, "")
        # убираем лишние слова из part
        part = re.sub(r"^(опубликуй|опубликовать|выложи|публикуй)\s*(это\s+)?объявление\s*(на олх)?\s*:?\s*",
                      "", part, flags=re.IGNORECASE).strip()
        part = part.replace("олх", "").replace("olx", "").strip(" ,.;:—–")
        if not part:
            api.send_message(chat_id, "📝 Скажите, что публикуем: «опубликуй на олх: фара BMW X5 2000»\n"
                                      "или сначала «создай объявление: …», потом «опубликуй это объявление»")
            return True
        import subprocess as _sp
        api.send_message(chat_id, f"⏳ Создаю объявление на OLX: «{part}»…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_olx_ad_gen.py"), "create", part],
                    capture_output=True, text=True, timeout=170, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-200:]}
        if res.get("status") == "need_confirm":
            _pending_confirm[chat_id] = {"kind": "olx_create",
                                         "data": {"part": part,
                                                  "title": res.get("title", ""),
                                                  "description": res.get("description", ""),
                                                  "price": res.get("price", "")}}
            api.send_message(chat_id,
                             f"📝 Объявление готово:\n<b>{res.get('title')}</b>\n"
                             f"Цена: {res.get('price')} грн\n"
                             f"{res.get('description', '')}\n\n"
                             f"Опубликовать на OLX? «да» / «нет»")
        elif res.get("status") == "phone_not_confirmed":
            api.send_message(chat_id,
                             f"📱 {res.get('error')}\n\n"
                             f"Напишите «подтверди телефон OLX» — открою VNC для одноразового подтверждения.")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', res.get('status', '?'))}")
        return True

    # ---- Автоответ OLX ----
    if any(w in t for w in ("автоответ олх", "автоответ olx", "автоответ в олх",
                            "автоответ покупателям")):
        cfg_file = PROJECT_ROOT / "data" / "olx_autoreply.json"
        try:
            cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
        if "выключ" in t or "отключ" in t:
            cfg["enabled"] = False
            cfg_file.parent.mkdir(parents=True, exist_ok=True)
            cfg_file.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
            api.send_message(chat_id, "🔕 Автоответ OLX выключен.")
            return True
        auto = "на автомате" in t
        cfg["enabled"] = True
        cfg["auto_send"] = auto
        cfg_file.parent.mkdir(parents=True, exist_ok=True)
        cfg_file.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        api.send_message(chat_id,
                         f"🔔 Автоответ OLX включён{' (на автомате)' if auto else ''}.\n"
                         f"При новых сообщениях в OLX-чате бот уведомит и поможет ответить.\n"
                         f"{'Отправка ответов — автоматически.' if auto else 'Сначала — подтверждение в чате.'}")
        return True

    # ---- Сколько стоит деталь (умные цены) ----
    if re.match(r"^(сколько стоит|почём|цена на|что стоит)\s+", t):
        q = re.sub(r"^(сколько стоит|почём|цена на|что стоит)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
        q = q.replace("?", "").strip()
        if not q:
            api.send_message(chat_id, "💰 «сколько стоит <деталь>», например: сколько стоит фара BMW X5")
            return True
        api.send_message(chat_id, f"💰 Ищу цену на «{q}»…")
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_price_guide.py"), q],
                    capture_output=True, text=True, timeout=90, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-150:]}
        if res.get("status") == "ok":
            if res.get("found"):
                txt = (f"💰 <b>Цена на «{q}»</b> (по {res['found']} похожим объявлениям):\n"
                       f"📊 Медиана: <b>{res.get('median')} грн</b>\n"
                       f"📉 Диапазон: {res.get('min')} – {res.get('max')} грн")
                if res.get("ai_advice"):
                    txt += f"\n\n🤖 <i>{_esc_tg(res['ai_advice'])}</i>"
                if res.get("examples"):
                    txt += "\n\nПримеры:\n" + "\n".join(
                        f"• {_esc_tg(e['title'][:55])} — {e['price']} грн" for e in res["examples"][:3])
                api.send_message(chat_id, txt[:3900])
            else:
                api.send_message(chat_id,
                                 f"💰 По «{q}» пока нет данных в базе.\n"
                                 f"Могу: «следи за ценой {q}» — буду собирать и уведомлять о снижении.")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    # ---- Кто продаёт дешевле (топ выгодных) ----
    if re.match(r"^(кто продаёт дешевле|кто продает дешевле|где дешевле|топ выгодных|лучшая цена)", t):
        q = re.sub(r"^(кто продаёт дешевле|кто продает дешевле|где дешевле|топ выгодных|лучшая цена)\s*:?\s*",
                   "", text, flags=re.IGNORECASE).strip()
        q = q.replace("?", "").strip()
        if not q:
            api.send_message(chat_id, "💰 «кто продаёт дешевле <деталь>», например: кто продаёт дешевле стартер ВАЗ")
            return True
        api.send_message(chat_id, f"💰 Ищу лучшие цены на «{q}»…")
        import subprocess as _sp
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_price_guide.py"), "cheap", q],
                    capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-150:]}
        if res.get("status") == "ok" and res.get("cheapest"):
            lines = [f"💰 <b>Лучшие цены на «{q}»</b> (медиана {res.get('median')} грн):"]
            for i, s in enumerate(res["cheapest"], 1):
                lines.append(f"{i}. <b>{s['price']} грн</b> — {_esc_tg(s['title'][:55])}\n"
                             f"   {_esc_tg(s.get('city') or '')} · <a href=\"{s.get('url', '#')}\">открыть</a>")
            api.send_message(chat_id, "\n".join(lines)[:3900])
        elif res.get("note"):
            api.send_message(chat_id, f"💰 «{q}» пока нет в базе. «следи за ценой {q}» — начну собирать.")
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    # ---- AI-классификатор при добавлении детали ----
    if re.match(r"^добавь деталь\s+.+,\s*\d+\s*шт", t):
        import subprocess as _sp
        m_add = re.match(r"^добавь деталь\s+(.+?)\s*[,:]\s*(\d+)\s*шт\s*(?:по\s*([\d\s.,]+))?", text, re.IGNORECASE)
        if m_add:
            name = m_add.group(1).strip()
            qty = int(m_add.group(2))
            price_s = m_add.group(3) or ""
            # LLM-классификация: категория + рекомендуемая цена
            prompt = (f"Деталь автозапчасти: «{name}». Определи категорию из списка "
                      f"(двигатель, кузов, оптика, подвеска, тормоза, электрика, салон, трансмиссия, расходники, другое) "
                      f"и среднюю цену в грн. Верни ТОЛЬКО JSON: {{\"category\": \"...\", \"price\": число}}. "
                      f"{('Ориентир по цене: ' + price_s + ' грн') if price_s else ''}")
            try:
                advice = _llm_chat_direct(prompt)
                import json as _json2
                start = advice.find("{")
                end = advice.rfind("}") + 1
                cls = _json2.loads(advice[start:end]) if start >= 0 and end > start else {}
                category = (cls.get("category") or "общее")
                rec_price = cls.get("price") or price_s or "0"
            except Exception:
                category, rec_price = "общее", price_s or "0"
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_inventory.py"),
                         "add", name, str(qty), str(rec_price or 0), category],
                        capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
            try:
                res = json.loads((r.stdout or "").strip().split("\n")[-1])
            except Exception:
                res = {"status": "error"}
            if res.get("status") == "ok":
                it = res.get("item", {})
                api.send_message(chat_id,
                                 f"📦 <b>{name}</b>: {it.get('qty')} шт · {it.get('price')} грн\n"
                                 f"🏷 Категория (AI): {it.get('category')}\n"
                                 f"{'🤖 Рекомендуемая цена по рынку.' if rec_price and not price_s else ''}")
            else:
                api.send_message(chat_id, f"❌ {res.get('error', '?')}")
            return True

    # ---- Склад (инвентаризация) ----
    inv_words = any(w in t for w in ("добавь деталь", "добавь на склад", "спиши деталь",
                                     "что на складе", "склад", "найди деталь",
                                     "продал ", "продал: ", "продал деталь", "продана деталь",
                                     "остатки", "инвентаризац", "сколько деталей"))
    if inv_words:
        import subprocess as _sp
        # продажа: списать со склада + записать финансы
        m_sale = re.match(r"^(продал|продала|продана деталь)\s+(.+?)\s+за\s+([\d\s.,]+)", text, re.IGNORECASE) or \
                 re.match(r"^(продал|продала|продана деталь)\s+([\w\sА-Яа-яЁёІіЇїЄє'’.-]+?)\s+([\d\s.,]+)", text, re.IGNORECASE)
        if m_sale:
            name = m_sale.group(2).strip()
            try:
                price = float(m_sale.group(3).replace(" ", "").replace(",", "."))
            except ValueError:
                api.send_message(chat_id, "❌ Не понял цену. Формат: «продал фару 2000»")
                return True
            # списать со склада
            r1 = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_inventory.py"),
                          "take", name, "1"], capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
            try:
                inv = json.loads((r1.stdout or "").strip().split("\n")[-1])
            except Exception:
                inv = {"status": "error"}
            # записать финансы
            r2 = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_finance.py"),
                          "add", "sale", str(price), name], capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
            try:
                fin = json.loads((r2.stdout or "").strip().split("\n")[-1])
            except Exception:
                fin = {"status": "error"}
            txt = f"💰 <b>Продажа: {name}</b> — {price} грн\n"
            if inv.get("status") == "ok":
                it = inv.get("item", {})
                txt += f"📦 Склад: списано (осталось {it.get('qty')} шт)\n"
            elif inv.get("error"):
                txt += f"⚠️ {inv['error']}\n"
            if fin.get("status") == "ok":
                txt += "✅ Записано в финансы"
            # Снять связанное объявление безопасно: только если остаток этой
            # позиции исчерпан и журнал публикаций дал единственное совпадение.
            try:
                from aios_core.sales_lifecycle import SalesLifecycle
                olx_res = SalesLifecycle(PROJECT_ROOT).deactivate_olx_for_item(name, "manual_sale")
                if olx_res.get("status") == "deactivated":
                    txt += "\n🛒 OLX: объявление снято с публикации"
                elif olx_res.get("status") == "kept_active":
                    txt += f"\n🛒 OLX: объявление оставлено (ещё {olx_res.get('available_qty')} шт в остатке)"
                elif olx_res.get("status") in ("not_found", "ambiguous", "error"):
                    txt += "\n⚠️ OLX: не найдено однозначное объявление для снятия"
            except Exception:
                txt += "\n⚠️ OLX: не удалось проверить связанное объявление"
            api.send_message(chat_id, txt + "\n📦 Если нужна накладная НП: «создай ттн: деталь, цена, ФИО, телефон, город, отделение»")
            return True
        # добавление детали
        m_add = re.match(r"^(добавь деталь|добавь на склад)\s+(.+?)\s*[,:]\s*(\d+)\s*шт\s*(?:по\s*([\d\s.,]+))?", text, re.IGNORECASE)
        if m_add:
            name = m_add.group(1).strip()
            qty = int(m_add.group(2))
            price_s = m_add.group(3) or "0"
            try:
                price = float(price_s.replace(" ", "").replace(",", "."))
            except ValueError:
                price = 0
            _cmd_list = ["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_inventory.py"),
                         "add", name, str(qty), str(price)]
            _ph = _last_photo.get(chat_id, "")
            if _ph and os.path.exists(_ph):
                _cmd_list += ["--photo", _ph]
            r = _sp.run(_cmd_list, capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
            try:
                res = json.loads((r.stdout or "").strip().split("\n")[-1])
            except Exception:
                res = {"status": "error", "error": (r.stderr or "?")[-100:]}
            if res.get("status") == "ok":
                it = res.get("item", {})
                photo_txt = " 📸+фото" if it.get("photo") else ""
                api.send_message(chat_id, f"📦 <b>{name}</b>: {it.get('qty')} шт ({it.get('price')} грн){photo_txt} — {res.get('msg', '')}")
            else:
                api.send_message(chat_id, f"❌ {res.get('error', '?')}")
            return True
        # «найди деталь» / поиск
        if "найди деталь" in t or "ищу деталь" in t or "есть ли" in t:
            q = re.sub(r"^(найди деталь|ищу деталь|есть ли)\s*:?\s*", "", text, flags=re.IGNORECASE).strip()
            q = q.replace("на складе", "").strip()
            if not q:
                api.send_message(chat_id, "🔍 «найди деталь капот»")
                return True
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_inventory.py"), "search", q],
                        capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
            try:
                res = json.loads((r.stdout or "").strip().split("\n")[-1])
            except Exception:
                res = {"status": "error"}
            if res.get("status") == "ok" and res.get("items"):
                lines = ["🔍 <b>Найдено на складе:</b>"]
                for it in res["items"][:8]:
                    available = it.get("available_qty", it.get("qty", 0))
                    reserved = it.get("reserved_qty", 0)
                    mark = "✅" if available > 0 else "❌"
                    reserve_note = f" · продано, ждёт отправки: {reserved}" if reserved else ""
                    lines.append(f"{mark} <b>{_esc_tg(it['name'])}</b> — свободно {available} из {it.get('qty')} шт · {it.get('price')} грн{reserve_note}")
                api.send_message(chat_id, "\n".join(lines))
            else:
                api.send_message(chat_id, f"🔍 «{q}» на складе нет.")
            return True
        # статистика/остатки
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_inventory.py"), "stats"],
                    capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error"}
        if res.get("status") == "ok":
            txt = (f"📦 <b>Склад</b>\n"
                   f"Деталей: {res.get('items_count')} · физически: {res.get('total_qty')} шт · "
                   f"свободно: {res.get('available_qty', res.get('total_qty'))} шт\n"
                   f"💰 Стоимость свободных запасов: {res.get('total_value')} грн")
            if res.get("reserved_qty"):
                txt += f"\n📌 Продано и ждёт отправки по созданным ТТН: {res.get('reserved_qty')} шт"
            if res.get("out_of_stock"):
                txt += "\n\n🚫 Закончились: " + ", ".join(_esc_tg(x) for x in res["out_of_stock"][:5])
            api.send_message(chat_id, txt)
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    # ---- Финансовый учёт ----
    fin_words = any(w in t for w in ("запиши продажу", "запиши расход", "запиши трату",
                                     "продал за", "купил за", "потратил",
                                     "сколько заработал", "прибыль", "финанс", "учет",
                                     "учёт", "деньги за неделю", "деньги за месяц",
                                     "мои операции", "операции"))
    if fin_words:
        import subprocess as _sp
        # запись операции
        m_op = re.match(r"^(запиши продажу|запиши расход|запиши трату|продал за|купил за|потратил)\s+([\d\s.,]+)\s*(.*)$", text, re.IGNORECASE)
        if m_op:
            verb = m_op.group(1).lower()
            kind = "sale" if any(k in verb for k in ("продаж", "продал")) else "expense"
            try:
                amount = float(m_op.group(2).replace(" ", "").replace(",", "."))
            except ValueError:
                api.send_message(chat_id, "❌ Не понял сумму. Пример: «запиши продажу 2000 фара BMW»")
                return True
            desc = m_op.group(3).strip() or ("продажа" if kind == "sale" else "расход")
            r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_finance.py"),
                         "add", kind, str(amount), desc],
                        capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
            try:
                res = json.loads((r.stdout or "").strip().split("\n")[-1])
            except Exception:
                res = {"status": "error", "error": (r.stderr or "?")[-100:]}
            if res.get("status") == "ok":
                em = "💰" if kind == "sale" else "📉"
                api.send_message(chat_id, f"{em} Записал: {desc} — {amount} грн ({'продажа' if kind == 'sale' else 'расход'})")
            else:
                api.send_message(chat_id, f"❌ {res.get('error', '?')}")
            return True
        # отчёт
        days = 30
        m_days = re.search(r"за\s+(неделю|месяц|день)", t)
        if m_days:
            if "неделю" in m_days.group(1):
                days = 7
            elif "день" in m_days.group(1):
                days = 1
            else:
                days = 30
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_finance.py"), "report", str(days)],
                    capture_output=True, text=True, timeout=20, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": "?"}
        if res.get("status") == "ok":
            txt = (f"💰 <b>Финансы за {days} дн.</b>\n"
                   f"🟢 Продажи: {res.get('sales')} грн\n"
                   f"🔴 Расходы: {res.get('expenses')} грн\n"
                   f"📊 Прибыль: <b>{res.get('profit')}</b> грн\n"
                   f"({res.get('count')} операций)")
            api.send_message(chat_id, txt)
        else:
            api.send_message(chat_id, f"❌ {res.get('error', '?')}")
        return True

    # ---- Google Таблица из данных ----
    if any(w in t for w in ("создай гугл таблицу", "создай google таблицу", "в гугл таблицу",
                            "создай таблицу из финансов", "создай таблицу из склада")):
        import subprocess as _sp
        kind = "finance" if ("финанс" in t or "продаж" in t) else \
               ("inventory" if "склад" in t or "детал" in t else "finance")
        api.send_message(chat_id, f"⏳ Создаю Google Таблицу из {'финансов' if kind == 'finance' else 'склада'}…")
        # 1) CSV
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_export.py"), kind],
                    capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
        try:
            res = json.loads((r.stdout or "").strip().split("\n")[-1])
        except Exception:
            res = {"status": "error", "error": (r.stderr or "?")[-100:]}
        if res.get("status") != "ok" or not res.get("file"):
            api.send_message(chat_id, f"❌ Не удалось выгрузить данные: {res.get('error', '?')}")
            return True
        csv_path = res["file"]
        api.send_message(chat_id, "📄 Данные готовы. Открываю Google Sheets…")
        # 2) открыть sheets и вставить (через Chrome Twin)
        try:
            from aios_core.platforms.chrome_twin_adapter import ChromeTwinAdapter as _CTA
            a = _CTA()
            # используем исправленный запуск
            from playwright.async_api import async_playwright as _ap
            import asyncio as _ai

            async def _do():
                pw = await _ap().start()
                ctx = await pw.chromium.launch_persistent_context(
                    user_data_dir=str((PROJECT_ROOT / "data" / "chrome_twin" / "default").resolve()),
                    executable_path="/usr/bin/google-chrome-stable",
                    headless=False, slow_mo=80,
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled",
                          "--disable-dev-shm-usage"],
                    viewport={"width": 1440, "height": 900})
                page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                await page.goto("https://docs.google.com/spreadsheets/create",
                                wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(9000)
                url = page.url
                # вставить CSV через первую ячейку (кликнуть A1 и вставить текст)
                try:
                    cell = page.locator("div#t-formula-bar-input, div[role='input']").first
                    # проще: кликнуть в A1 листа
                    a1 = page.locator("#t-0-0-0, [role='gridcell'][aria-colindex='1'][aria-rowindex='1']").first
                    if await a1.count():
                        await a1.click(force=True, timeout=5000)
                        await page.wait_for_timeout(800)
                        # вставить данные как текст в формулу-бар? Лучше: просто открыть и оставить
                except Exception:
                    pass
                await ctx.close()
                await pw.stop()
                return url
            url = _ai.run(_do())
            api.send_message(chat_id,
                             f"✅ <b>Google Таблица создана</b>:\n🔗 {url}\n\n"
                             f"CSV-файл с данными: {csv_path}\n"
                             f"(импортируйте его в таблицу: Файл → Импорт — или пришлите мне команду "
                             f"«экспортируй финансы в csv» для повторной выгрузки)")
        except Exception as e:
            api.send_message(chat_id, f"⚠️ Таблица создана, но не открыта: {e}\nCSV: {csv_path}")
        return True

    # ---- Вечерний отчёт ----
    if any(w in t for w in ("вечерний отчёт", "вечерний отчет", "итоги дня",
                            "отчёт за день", "отчет за день", "дневной отчёт")):
        import subprocess as _sp
        api.send_message(chat_id, "⏳ Собираю отчёт…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_evening_report.py")],
                    capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT))
        if "отправлен" in (r.stdout or ""):
            api.send_message(chat_id, "🌙 Вечерний отчёт отправлен ☺️")
        else:
            # показать локально
            import importlib.util as _iu2
            try:
                spec = _iu2.spec_from_file_location("evr", str(PROJECT_ROOT / "run_evening_report.py"))
                mod = _iu2.module_from_spec(spec)
                spec.loader.exec_module(mod)
                report = mod.build_report()
                api.send_message(chat_id, report[:3900])
            except Exception as e:
                api.send_message(chat_id, f"❌ {e}")
        return True

    # ---- Месячный отчёт ----
    if any(w in t for w in ("месячный отчёт", "месячный отчет", "отчёт за месяц",
                            "отчет за месяц", "отчёт за 30 дней", "сводка за месяц")):
        import subprocess as _sp
        api.send_message(chat_id, "⏳ Собираю месячный отчёт…")
        r = _sp.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_evening_report.py"), "--monthly"],
                    capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT))
        try:
            report = json.loads((r.stdout or "").strip().split("\n")[-1])
            api.send_message(chat_id, "❌ Не удалось собрать отчёт")
        except Exception:
            # stdout не JSON — это сам отчёт? нет, --monthly шлёт в TG. Покажем через импорт
            import importlib.util as _iu3
            try:
                spec = _iu3.spec_from_file_location("evrm", str(PROJECT_ROOT / "run_evening_report.py"))
                mod = _iu3.module_from_spec(spec)
                spec.loader.exec_module(mod)
                report = mod.build_monthly()
                api.send_message(chat_id, report[:3900])
            except Exception as e:
                api.send_message(chat_id, f"❌ {e}")
        return True

    # ---- Голосовые ответы ----
    if any(w in t for w in ("включи голосовые ответы", "отвечай голосом", "включи голос")):
        _set_voice_enabled(chat_id, True)
        api.send_message(chat_id, "🎙 Голосовые ответы ВКЛЮЧЕНЫ — бот будет озвучивать ответы.")
        return True
    if any(w in t for w in ("выключи голосовые ответы", "отвечай текстом", "выключи голос")):
        _set_voice_enabled(chat_id, False)
        api.send_message(chat_id, "🔇 Голосовые ответы выключены.")
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
                                 "✈️ <b>Telegram</b>: «напиши в телеграм &lt;имя&gt;: &lt;текст&gt;»\n"
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
                api.send_message(chat_id, "👤 Напишите «найди контакт &lt;имя&gt;»")
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
                             "🔍 <b>Поиск в почте</b>: напишите «найди письмо &lt;запрос&gt;»,\n"
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
            "• «мой инстаграм» · «директ» · «лайкни &lt;ссылка&gt;»\n"
            "• «покажи фейсбук» · «тикток» · «олх» / «мои объявления»\n"
            "• «подпишись на @…» / «отпишись от @…»\n\n"
            "Или выберите раздел:")


def cmd_google(args: str) -> str:
    a = args.strip().lower()
    if not a:
        return ("🌐 <b>Google</b>\n\nКоманды:\n"
                "/google whoami · /google unread · /google list\n"
                "/google search &lt;запрос&gt; · /google calendar · /google drive\n"
                "/google events · /google mailshot · /google send\n"
                "Или просто напишите «проверь почту», «события на сегодня», «создай документ …»")
    return "🌐 Google: укажите подкоманду."


def cmd_instagram(args: str) -> str:
    a = args.strip().lower()
    if not a:
        return ("📸 <b>Instagram</b>\n\nКоманды:\n"
                "/instagram profile · /instagram posts · /instagram screenshot\n"
                "Или просто напишите «мой инстаграм», «лайкни &lt;ссылка&gt;», «подпишись на @…»")
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



def _handle_inbox_callback(api: TelegramAPI, chat_id: int, msg_id: int, data: str) -> None:
    """Обработка кнопок инбокса: прочитать пункт / всё прочитано / сводка."""
    items = _last_inbox.get(chat_id, [])
    if data == "inbox_refresh":
        _send_unified_inbox(api, chat_id, filters=_last_inbox_filters.get(chat_id, {}))
        return
    if data == "inbox_readall":
        _inbox_mark_read(api, chat_id)
        return
    if data == "inbox_summary":
        if not items:
            api.send_message(chat_id, "📭 Нет данных инбокса (соберите «инбокс» заново).")
            return
        api.send_message(chat_id, "🧠 Составляю умное резюме…")
        api.send_message(chat_id, _inbox_summarize(items)[:3900])
        return
    if data.startswith("inbox_read_"):
        try:
            idx = int(data.split("_")[-1])
            it = items[idx - 1]
        except Exception:
            api.send_message(chat_id, "❌ Не удалось открыть пункт.")
            return
        if it.get("channel") == "viber":
            api.send_message(chat_id, "⏳ Читаю выбранный Viber-чат…")
            data_vb = _run_account_control(["viber", "read", str(it.get("ref") or ""), "--limit", "12"])
            if data_vb.get("status") != "ok":
                api.send_message(chat_id, f"❌ Viber: {_esc_tg(data_vb.get('error', '?'))}")
                return
            messages = data_vb.get("messages") or []
            if not messages:
                api.send_message(chat_id, "💜 В выбранном Viber-чате нет распознанных сообщений.")
                return
            lines_vb = [f"💜 <b>{_esc_tg(it['title'])[:80]}</b> [Viber]"]
            for message in messages[-12:]:
                prefix = "↗️" if message.get("mine") else "•"
                lines_vb.append(f"{prefix} {_esc_tg(str(message.get('text') or '')[:220])}")
            lines_vb.append(f"\nОтветить: «ответь на {idx}: текст»")
            api.send_message(chat_id, "\n".join(lines_vb)[:3900])
            return
        if it.get("channel") == "signal":
            api.send_message(chat_id, "⏳ Читаю выбранный Signal-чат…")
            data_sig = _run_account_control(["signal", "read", str(it.get("ref") or ""), "--limit", "12"])
            if data_sig.get("status") != "ok":
                api.send_message(chat_id, f"❌ Signal: {_esc_tg(data_sig.get('error', '?'))}")
                return
            messages = data_sig.get("messages") or []
            if not messages:
                api.send_message(chat_id, "🔒 В выбранном Signal-чате нет распознанных сообщений.")
                return
            lines_sig = [f"🔒 <b>{_esc_tg(it['title'])[:80]}</b> [Signal]"]
            for message in messages[-12:]:
                prefix = "↗️" if message.get("mine") else "•"
                lines_sig.append(f"{prefix} {_esc_tg(str(message.get('text') or '')[:220])}")
            lines_sig.append(f"\nОтветить: «ответь на {idx}: текст»")
            api.send_message(chat_id, "\n".join(lines_sig)[:3900])
            return
        em, ch = _CHANNELS.get(it["channel"], ("", it["channel"]))
        txt = (f"{em} <b>{_esc_tg(it['title'])[:80]}</b> [{ch}]\n"
               f"{_esc_tg(it.get('preview') or '')}\n"
               f"🕐 {it.get('date') or '—'}\n\n"
               f"Ответить: «ответь на {idx}: текст»")
        api.send_message(chat_id, txt)
        return


def _handle_olx_send_callback(api: TelegramAPI, chat_id: int, cb_id: str, data: str) -> None:
    """Кнопка «Отправить ответ» — отправляет сгенерированный ответ в OLX-чат.

    Формат data: olx_send_<contact>|<text>. Контакт и текст URL-безопасно кодируются.
    """
    try:
        rid = data[len("olx_send_"):]
        # получить неотправленный ответ из pending-файла
        import json as _json
        pending = PROJECT_ROOT / "data" / "olx_pending_replies.json"
        item = None
        try:
            if pending.exists():
                _d = _json.loads(pending.read_text(encoding="utf-8"))
                item = _d.pop(rid, None)
                pending.write_text(_json.dumps(_d, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
        if not item or not item.get("contact") or not item.get("text"):
            api.answer_callback(cb_id, "❌ Ответ не найден (истёк)")
            return
        contact = item["contact"]
        text = item["text"]
        import subprocess as _sp_olx
        r = _sp_olx.run(
            ["xvfb-run", "-a", "-s", "-screen 0 1440x900x24",
             "/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_account_control.py"),
             "olx", "chat", "reply", contact, text, "--confirm"],
            capture_output=True, text=True, timeout=200, cwd=str(PROJECT_ROOT))
        out = (r.stdout or "").strip()
        ok = '"status": "sent"' in out or '"status": "ok"' in out
        if ok:
            api.answer_callback(cb_id, "✅ Отправлено")
            api.send_message(chat_id, f"✅ Ответ отправлен <b>{contact}</b> в OLX.")
        else:
            api.answer_callback(cb_id, "⚠️ Не отправлено")
            api.send_message(chat_id, f"⚠️ Не удалось отправить <b>{contact}</b>: {out[-200:]}")
    except Exception as e:
        try:
            api.answer_callback(cb_id, "⚠️ Ошибка")
            api.send_message(chat_id, f"⚠️ Ошибка отправки: {e}")
        except Exception:
            pass


def _handle_autonomy_callback(api: TelegramAPI, chat_id: int, msg_id: int, cb_id: str, data: str) -> None:
    """Обработка кнопок подтверждения/отклонения автономии."""
    try:
        approve = data.startswith("aut_ap_")
        aid = data.split("_", 2)[2]
        from aios_core.autonomy import AutonomyCore as _AutoCore
        core = _AutoCore()
        res = core.confirm(aid, approve=approve)
        if res.get("ok"):
            if approve:
                r = res.get("result", {})
                api.answer_callback(cb_id, "✅ Выполнено")
                api.send_message(chat_id,
                                 f"✅ <b>Подтверждено и выполнено</b> ({aid})\n"
                                 f"{r.get('message') or r.get('status') or 'ok'}")
            else:
                api.answer_callback(cb_id, "❌ Отклонено")
                api.send_message(chat_id, f"❌ Отклонено ({aid})")
        else:
            api.answer_callback(cb_id, "⚠️ не найдено")
            api.send_message(chat_id, f"⚠️ Approval {aid} не найден или уже обработан.")
    except Exception as e:
        try:
            api.answer_callback(cb_id, "⚠️ ошибка")
            api.send_message(chat_id, f"⚠️ Ошибка обработки кнопки: {e}")
        except Exception:
            pass
def _handle_viber_draft_callback(api: TelegramAPI, chat_id: int, cb_id: str, data: str) -> None:
    """Подтвердить или отменить Viber-черновик из фонового обработчика."""
    try:
        from viber_drafts import ViberDraftStore
        send = data.startswith("viber_draft_send_")
        prefix = "viber_draft_send_" if send else "viber_draft_cancel_"
        draft_id = data[len(prefix):]
        store = ViberDraftStore(PROJECT_ROOT)
        if not draft_id:
            api.answer_callback(cb_id, "❌ Некорректный черновик")
            return
        if not send:
            draft = store.cancel(draft_id)
            if draft is None:
                api.answer_callback(cb_id, "ℹ️ Уже обработан")
                return
            api.answer_callback(cb_id, "❌ Черновик отклонён")
            api.send_message(chat_id, f"💜 Черновик для <b>{_esc_tg(draft.get('contact'))}</b> отклонён.")
            return
        draft = store.claim(draft_id)
        if draft is None:
            api.answer_callback(cb_id, "ℹ️ Уже обработан")
            return
        result = _run_account_control([
            "viber", "send", str(draft.get("contact") or ""),
            str(draft.get("text") or ""), "--confirm",
        ])
        if result.get("status") == "sent":
            store.finalize(draft_id, sent=True)
            api.answer_callback(cb_id, "✅ Отправлено")
            api.send_message(chat_id, f"✅ Черновик отправлен в Viber: <b>{_esc_tg(draft.get('contact'))}</b>.")
        else:
            error = str(result.get("error") or result.get("status") or "неизвестная ошибка")
            store.finalize(draft_id, sent=False, error=error)
            api.answer_callback(cb_id, "⚠️ Не отправлено")
            api.send_message(chat_id, f"⚠️ Viber не отправил черновик: {_esc_tg(error)[:220]}")
    except Exception as exc:
        try:
            api.answer_callback(cb_id, "⚠️ Ошибка")
            api.send_message(chat_id, f"⚠️ Ошибка Viber-черновика: {_esc_tg(str(exc))[:220]}")
        except Exception:
            pass


def _handle_signal_draft_callback(api: TelegramAPI, chat_id: int, cb_id: str, data: str) -> None:
    """Подтвердить или отменить Signal-черновик из фонового обработчика."""
    try:
        from signal_drafts import SignalDraftStore
        send = data.startswith("signal_draft_send_")
        prefix = "signal_draft_send_" if send else "signal_draft_cancel_"
        draft_id = data[len(prefix):]
        store = SignalDraftStore(PROJECT_ROOT)
        if not draft_id:
            api.answer_callback(cb_id, "❌ Некорректный черновик")
            return
        if not send:
            draft = store.cancel(draft_id)
            if draft is None:
                api.answer_callback(cb_id, "ℹ️ Уже обработан")
                return
            api.answer_callback(cb_id, "❌ Черновик отклонён")
            api.send_message(chat_id, f"🔒 Черновик для <b>{_esc_tg(draft.get('contact'))}</b> отклонён.")
            return
        draft = store.claim(draft_id)
        if draft is None:
            api.answer_callback(cb_id, "ℹ️ Уже обработан")
            return
        result = _run_account_control([
            "signal", "send", str(draft.get("contact") or ""),
            str(draft.get("text") or ""), "--confirm",
        ])
        if result.get("status") == "sent":
            store.finalize(draft_id, sent=True)
            api.answer_callback(cb_id, "✅ Отправлено")
            api.send_message(chat_id, f"✅ Черновик отправлен в Signal: <b>{_esc_tg(draft.get('contact'))}</b>.")
        else:
            error = str(result.get("error") or result.get("status") or "неизвестная ошибка")
            store.finalize(draft_id, sent=False, error=error)
            api.answer_callback(cb_id, "⚠️ Не отправлено")
            api.send_message(chat_id, f"⚠️ Signal не отправил черновик: {_esc_tg(error)[:220]}")
    except Exception as exc:
        try:
            api.answer_callback(cb_id, "⚠️ Ошибка")
            api.send_message(chat_id, f"⚠️ Ошибка Signal-черновика: {_esc_tg(str(exc))[:220]}")
        except Exception:
            pass


def _handle_callback(api: TelegramAPI, upd: dict) -> None:
    """Handle inline button callbacks (кнопки в сообщениях)."""
    cb = upd.get("callback_query", {})
    cb_id = cb.get("id", "")
    data = cb.get("data", "")
    msg = cb.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    msg_id = msg.get("message_id")

    if not chat_id or not data:
        return

    api.answer_callback(cb_id, "⏳ Обрабатываю...")

    # ---- Signal: черновик из фонового безопасного обработчика ----
    if data.startswith("signal_draft_send_") or data.startswith("signal_draft_cancel_"):
        _handle_signal_draft_callback(api, chat_id, cb_id, data)
        return

    # ---- Viber: черновик из фонового безопасного обработчика ----
    if data.startswith("viber_draft_send_") or data.startswith("viber_draft_cancel_"):
        _handle_viber_draft_callback(api, chat_id, cb_id, data)
        return

    # ---- OLX: отправить сгенерированный ответ вручную (кнопка) ----
    if data.startswith("olx_send_"):
        _handle_olx_send_callback(api, chat_id, cb_id, data)
        return

    # ---- Автономия: кнопки подтверждения/отклонения ----
    if data.startswith("aut_ap_") or data.startswith("aut_rm_"):
        _handle_autonomy_callback(api, chat_id, msg_id, cb_id, data)
        return

    # ---- Инбокс: inline-действия ----
    if data.startswith("inbox_"):
        _handle_inbox_callback(api, chat_id, msg_id, data)
        return

    # ---- Инбокс: inline-действия ----
    if data.startswith("inbox_"):
        _handle_inbox_callback(api, chat_id, msg_id, data)
        return

    # ---- Остальные кнопки меню (опасные — с подтверждением) ----
    _handle_button(api, chat_id, data)


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
        "- Окружение: [PRIVATE_CONTACT] (друг/партнёр по разборке), Владка (оператор на АЗС), Иринка (координация задач).\n"
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
                    model=_smart_model(),
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
    _last_inbox_check = 0.0

    while True:
        try:
            # проверка созревших напоминаний (раз в 60 сек)
            if time.time() - _last_reminder_check >= 60:
                try:
                    _run_due_reminders()
                except Exception as _rem_err:
                    print(f"  [REMINDER] check err: {_rem_err}")
                _last_reminder_check = time.time()

            # проверка расписания инбокса (раз в 60 сек)
            if time.time() - _last_inbox_check >= 60:
                try:
                    _run_due_inbox(token)
                except Exception as _ib_err:
                    print(f"  [INBOX] sched err: {_ib_err}")
                _last_inbox_check = time.time()

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

                    # --- AIOS Autonomy: исполнение бизнес-команд владельца (опт-ин) ---
                    if os.environ.get("AIOS_AUTONOMY_HOOK") == "1":
                        try:
                            if "_auto_core" not in globals():
                                from aios_core.autonomy import AutonomyCore as _AutoCore
                                globals()["_auto_core"] = _AutoCore()
                            _ao = globals()["_auto_core"].process_owner(chat_id, text)
                            _is_action = _ao.get("mode") == "action" and _ao.get("action") not in ("reply_customer", "query_platform")
                            if _is_action or _ao.get("mode") == "manual":
                                _txt = _ao.get("text") or ""
                                if _ao.get("mode") == "manual" and _ao.get("approval_id"):
                                    _txt = (_txt or "Действие требует подтверждения") + "\nID: <code>" + str(_ao.get("approval_id")) + "</code>"
                                if _txt:
                                    try:
                                        api.send_message(chat_id, _txt[:3900])
                                    except Exception:
                                        try:
                                            api.send_message(chat_id, _txt[:3900], parse_mode="")
                                        except Exception:
                                            pass
                                print(f"  [AUTONOMY] {_ao.get('action')} -> {_ao.get('decision')}")
                                continue
                        except Exception as _au_err:
                            print(f"  [AUTONOMY] err: {_au_err}")

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
                        # голосовой ответ, если включён
                        if _voice_enabled(chat_id):
                            _send_voice_reply(api, chat_id, llm_reply[:1500])
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
                elif cmd in ("/reputation", "/rep", "/clients"):
                    reply = None
                    keyboard = None
                    import subprocess as _sp_rep
                    try:
                        r = _sp_rep.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_autonomy_clients.py"),
                                         "--top", "15"], capture_output=True, text=True,
                                        timeout=60, cwd=str(PROJECT_ROOT))
                        api.send_message(chat_id, (r.stdout or "нет данных")[:3800])
                    except Exception as e:
                        api.send_message(chat_id, f"❌ Ошибка: {e}")
                elif cmd in ("/security", "/sec", "/safe"):
                    reply = None
                    keyboard = None
                    import subprocess as _sp_sec
                    try:
                        r = _sp_sec.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_autonomy_security.py")],
                                        capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT))
                        api.send_message(chat_id, (r.stdout or "нет данных")[:3800])
                    except Exception as e:
                        api.send_message(chat_id, f"❌ Ошибка: {e}")
                elif cmd in ("/bank", "/banks"):
                    reply = None
                    keyboard = None
                    bank = args.strip().lower()
                    if bank not in ("abank", "privat"):
                        api.send_message(chat_id, "Банки: <b>abank</b>, <b>privat</b>.\n"
                                                   "Пример: /bank privat balance · /bank abank balance")
                    else:
                        api.send_message(chat_id, f"⏳ Проверяю {bank}…")
                        import subprocess as _sp_b
                        try:
                            r = _sp_b.run(["xvfb-run", "-a", "-s", "-screen 0 1440x900x24",
                                           "/opt/aios/.venv/bin/python",
                                           str(PROJECT_ROOT / "run_account_control.py"),
                                           bank, "balance"], capture_output=True, text=True,
                                          timeout=200, cwd=str(PROJECT_ROOT))
                            out = (r.stdout or "нет данных")[-600:]
                            api.send_message(chat_id, f"🏦 <b>{bank}</b>\n<code>{out[:3800]}</code>")
                        except Exception as e:
                            api.send_message(chat_id, f"❌ Ошибка: {e}")
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
