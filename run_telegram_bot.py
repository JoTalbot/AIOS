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

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# ---------------------------------------------------------------------------
# Telegram API helpers (zero-dependency)
# ---------------------------------------------------------------------------


class TelegramAPI:
    """Minimal Telegram Bot API client (polling mode)."""

    def __init__(self, token: str) -> None:
        self._base = f"https://api.telegram.org/bot{token}"

    def _request(self, method: str, data: dict | None = None) -> dict:
        url = f"{self._base}/{method}"
        body = json.dumps(data or {}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    def get_updates(self, offset: int = 0) -> list[dict]:
        result = self._request("getUpdates", {"offset": offset, "timeout": 30})
        return result.get("result", [])

    def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML",
                     disable_web_page_preview: bool = True) -> dict:
        return self._request(
            "sendMessage",
            {"chat_id": chat_id, "text": text[:4000], "parse_mode": parse_mode,
             "disable_web_page_preview": disable_web_page_preview},
        )


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
def cmd_start() -> str:
    return (
        "🤖 <b>AIOS Telegram Bot</b>\n\n"
        "Команды:\n"
        "  /stats  — статистика системы\n"
        "  /status — сводка по платформам\n"
        "  /olx    — статистика OLX\n"
        "  /olx_sub &lt;запрос&gt; [min max] — подписка на новые объявления\n"
        "  /olx_unsub [запрос] — отписка\n"
        "  /olx_list — список моих подписок\n"
        "  /olx_latest &lt;запрос&gt; [N] — последние объявления\n"
        "  /olx_analytics &lt;запрос&gt; — аналитика цен (AI)\n"
        "  /help   — помощь\n\n"
        "<i>v9.3.2 · JoTalbot/AIOS · Dashboard: https://api.autosklo.org.ua/aios/</i>"
    )


@_safe
def cmd_stats() -> str:
    from aios_core.container import container

    db = container.db()
    orch = container.orchestrator()
    bm = container.backup_manager()
    db_stats = db.stats()
    orch_stats = orch.stats()
    bu_health = bm.health_report()

    tables_info = "\n".join(
        f"    <code>{t}</code>: {c} строк" for t, c in sorted(db_stats.get("tables", {}).items())
    )
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
    for p in plats:
        lines.append(f"  • <code>{p.name}</code> — <code>{p.android_package}</code>")
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
    import sqlite3
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
        last_run = conn.execute(
            "SELECT ts, parsed FROM collection_runs ORDER BY ts DESC LIMIT 1"
        ).fetchone()
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
        try:
            maybe_max = float(parts[-1].replace(",", "."))
            # Two-arg: only max? Or single numeric = min? Be strict: need both.
            # For simplicity, treat single trailing number as max if preceded by query
        except ValueError:
            pass
    query = " ".join(parts)
    if not query:
        return "❌ Укажите поисковый запрос."
    subs = olx_alerts.init_subs_db()
    olx_alerts.subscribe_chat(subs, chat_id, query, username=username, first_name=first_name,
                              min_price=min_p, max_price=max_p)
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
    import sqlite3
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
                "SELECT * FROM ads WHERE query=? AND active=1 ORDER BY collected_at DESC LIMIT ?",
                (query, n)).fetchall()
        else:
            # Use first subscribed query
            import olx_alerts
            subs = olx_alerts.init_subs_db()
            items = olx_alerts.list_subscriptions(subs, chat_id)
            if not items:
                return "ℹ️ Укажите запрос: <code>/olx_latest iPhone</code> или подпишитесь через /olx_sub"
            query = items[0]["query"]
            rows = conn.execute(
                "SELECT * FROM ads WHERE query=? AND active=1 ORDER BY collected_at DESC LIMIT ?",
                (query, n)).fetchall()
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
            out.append(f"• <a href=\"{url}\">{title}</a>\n  {price_str} · 📍{city}")
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
            "ORDER BY price_value ASC LIMIT 5", (query,)).fetchall()
        out = [f"📊 <b>AI-аналитика цен</b> «{query}»:\n",
               f"  📦 Объявлений в выборке: <b>{stats.count}</b>",
               f"  💸 Мин: <b>{int(stats.min_p):,} грн</b>",
               f"  📈 Макс: <b>{int(stats.max_p):,} грн</b>",
               f"  ⚖️ Медиана: <b>{int(stats.median):,} грн</b>",
               f"  📉 P10 (очень дёшево): <b>{int(stats.p10):,} грн</b>",
               f"  📈 P90 (очень дорого): <b>{int(stats.p90):,} грн</b>",
               f"  🧮 Средняя: <b>{stats.avg:,.0f} грн</b>\n",
               "🔥 <b>ТОП-5 самых дешёвых:</b>"]
        for r in cheapest:
            title = (r["title"] or "")[:55]
            out.append(f"  • <a href=\"{r['url']}\">{title}</a> — {int(r['price_value']):,} грн ({r['city']})")
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
        "  /help — эта справка\n\n"
        "<i>Бот работает в polling-режиме. Алерты приходят автоматически после каждого цикла сбора (каждые 30 мин).</i>"
    )


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


def run_bot(token: str) -> None:
    api = TelegramAPI(token)
    offset = 0

    print("🤖 AIOS Telegram Bot запущен (v9.3.2 with OLX alerts)")
    print("   Ожидание сообщений...\n")

    while True:
        try:
            updates = api.get_updates(offset)
            for upd in updates:
                offset = upd["update_id"] + 1
                msg = upd.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                chat_type = msg.get("chat", {}).get("type")
                username = msg.get("from", {}).get("username")
                first_name = msg.get("from", {}).get("first_name")
                text = (msg.get("text") or "").strip()

                if not chat_id or not text:
                    continue
                cmd, args = parse_command(text)
                if not cmd.startswith("/"):
                    continue

                reply = None
                if cmd == "/start":
                    reply = cmd_start()
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
                elif cmd == "/help":
                    reply = cmd_help()
                else:
                    reply = "ℹ️ Неизвестная команда. /help для списка."

                if reply:
                    api.send_message(chat_id, reply)
                    print(f"  → ответил на {cmd} (chat {chat_id})")

        except KeyboardInterrupt:
            print("\n👋 Бот остановлен.")
            break
        except Exception as exc:
            print(f"⚠️ Ошибка polling: {exc}")
            time.sleep(5)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    TOKEN = os.environ.get("AIOS_TELEGRAM_TOKEN")
    if not TOKEN:
        print("❌ Установите AIOS_TELEGRAM_TOKEN")
        sys.exit(1)

    run_bot(TOKEN)
