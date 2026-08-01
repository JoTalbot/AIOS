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
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

_env_path = Path(__file__).resolve().parent / ".env"
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
    return "🤖 <b>AIOS Control Panel</b>\n\nВыберите раздел:"

MAIN_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "🧠 Кодер"}, {"text": "📊 Статистика"}],
        [{"text": "🛒 OLX"}, {"text": "📱 Платформы"}],
        [{"text": "🖥 Сервер"}, {"text": "🐳 Docker"}],
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
        "  /help — эта справка\n\n"
        "<i>Бот работает в polling-режиме. Алерты приходят автоматически после каждого цикла сбора (каждые 30 мин).</i>"
    )




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
        mod_name, "/app/aios_core/meta_cognitive_self_coder.py"
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
_paused = False
_chat_history: dict[int, list[dict]] = {}  # chat_id -> message history
MAX_HISTORY = 20  # keep last 20 messages per chat


def _handle_button(api: TelegramAPI, chat_id: int, data: str) -> None:
    """Handle button press by action name."""
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

    if data == "menu_back":
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
            spec = _iu.spec_from_file_location("lb_k", "/app/aios_core/llm_balancer.py")
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
            with open("/app/data/coder_backlog.json") as f:
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
            spec = _iu.spec_from_file_location("lb_b", "/app/aios_core/llm_balancer.py")
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
        spec = _iu.spec_from_file_location("lb_s", "/app/aios_core/llm_balancer.py")
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
        "You are AIOS Hermes, an assistant with FULL ROOT ACCESS on this Ubuntu/Docker server.\n"
        "Project: /root/AIOS.\n"
        "To run a shell command, output it in <cmd>...</cmd> tags (one per response).\n"
        "Read files with <cmd>cat ...</cmd>, list with <cmd>ls ...</cmd>, manage services with <cmd>systemctl ...</cmd>.\n"
        "You may read/write files, manage services, install packages.\n"
        "Avoid destructive commands (rm -rf).\n"
        "Answer in the user language (RU/EN). Be concise. If asked to code/fix - do it directly.\n"
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
        with open("/app/data/.llm_keys.json") as _kf:
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
    # Bot menu
    "▶️ Старт": "bot_start",
    "⏸️ Пауза": "bot_pause",
    "🔄 Рестарт": "bot_restart",
    "⏹️ Стоп": "bot_stop",
    "📊 Статус бота": "bot_status",
}



def run_bot(token: str) -> None:
    api = TelegramAPI(token)
    offset = 0

    print("🤖 AIOS Telegram Bot запущен (v10.0 with inline menu)")
    print("   Ожидание сообщений...\n")

    while True:
        try:
            updates = api.get_updates(offset)
            for upd in updates:
                offset = upd["update_id"] + 1

                # Handle callback queries (button presses) — always process even when paused
                if "callback_query" in upd:
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

                if not chat_id or not text:
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
