"""Autonomy Executor — исполнение разрешённых действий.

Использует те же исполнители, что и существующие команды бота:
  * ``run_account_control.py`` — платформенные действия (OLX-чат, IG, FB, NP, TG)
  * ``run_finance.py``  — продажи/расходы (data/finance.json)
  * ``run_inventory.py`` — склад (data/inventory.json)
Это гарантирует консистентность данных с остальной системой.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PY = "/opt/aios/.venv/bin/python"


def _run_ac(args: list[str], timeout: int = 160) -> dict:
    """Запустить run_account_control.py (как бот)."""
    helper = str(PROJECT_ROOT / "run_account_control.py")
    # viber — нативный десктоп; google IMAP/SMTP — без X; остальное — браузер
    if args and args[0] == "viber":
        needs_x = False
    else:
        needs_x = not (len(args) >= 2 and args[0] == "google"
                       and args[1] in ("gmail_list", "gmail_send", "gmail_search", "open"))
    cmd = (["xvfb-run", "-a", "-s", "-screen 0 1440x900x24", PY, helper] + args) if needs_x \
        else ([PY, helper] + args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(PROJECT_ROOT))
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "timeout (браузер занят)"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}
    out = (r.stdout or "").strip()
    if not out:
        return {"status": "error", "error": (r.stderr or "пустой ответ")[-400:]}
    try:
        start = out.find("{")
        return json.loads(out[start:]) if start >= 0 else {"status": "error", "error": out[-400:]}
    except Exception:
        return {"status": "error", "error": out[-400:]}


def _finance() -> Any:
    import run_finance
    return run_finance


def _inventory() -> Any:
    import run_inventory
    return run_inventory


class Executor:
    def __init__(self, root: Path | None = None):
        self.root = root or PROJECT_ROOT

    def execute(self, proposal: dict) -> dict:
        """Выполнить действие proposal. Возвращает результат {status, message, ...}."""
        action = proposal.get("action", "")
        params = proposal.get("params", {}) or {}
        platform = proposal.get("platform", "")
        chat = proposal.get("chat", "")

        try:
            handler = getattr(self, f"_do_{action}", None)
            if handler is None:
                return {"status": "error", "error": f"Нет исполнителя для {action}"}
            return handler(params, platform, chat)
        except Exception as e:
            return {"status": "error", "error": str(e)[:300]}

    # ---- Учёт ----
    def _do_log_sale(self, p, platform, chat):
        item = str(p.get("item") or p.get("sku") or "").strip()
        amount = float(p.get("amount") or 0)
        if amount <= 0 or not item:
            return {"status": "error", "error": "Нужны item и amount>0"}
        res = _finance().add("sale", amount, item)
        # авто-списание со склада (если такой товар есть)
        inv_result = None
        try:
            inv_result = _inventory().take(item, 1)
        except Exception:
            inv_result = {"status": "error", "error": "inventory недоступен"}
        msg = f"Продажа: {item} = {amount} грн"
        if inv_result and inv_result.get("status") == "ok":
            msg += " · склад обновлён"
        elif inv_result and inv_result.get("error"):
            msg += f" · склад: {inv_result['error']}"
        # После ручной продажи также снимаем связанное объявление OLX, если
        # свободный остаток этой позиции закончился. Явный ad_id имеет приоритет.
        ad_id = str(p.get("ad_id") or "").strip()
        olx_auto_res = None
        if not ad_id and inv_result and inv_result.get("status") == "ok":
            try:
                from aios_core.sales_lifecycle import SalesLifecycle
                olx_auto_res = SalesLifecycle(Path(self.root)).deactivate_olx_for_item(item, "manual_sale")
                if olx_auto_res.get("status") == "deactivated":
                    msg += " · объявление OLX снято"
                elif olx_auto_res.get("status") in ("not_found", "ambiguous", "error"):
                    msg += " · OLX: нужна ручная проверка"
            except Exception:
                olx_auto_res = {"status": "error", "error": "автоснятие OLX недоступно"}
        ad_res = None
        if ad_id:
            ad_res = _run_ac(["olx", "delete", ad_id, "--confirm"], timeout=170)
            if ad_res.get("status") == "ok":
                msg += " · объявление снято"
            else:
                msg += f" · объявление: {ad_res.get('error', 'не снято')}"
        # опциональное напоминание в календаре (AIOS_SALE_CALENDAR=1)
        cal_res = None
        import os as _os
        if _os.environ.get("AIOS_SALE_CALENDAR", "0") == "1":
            cal_res = _run_ac(["google", "calendar_add", "--title", f"Продажа: {item}",
                               "--desc", f"Продано {item} за {amount} грн",
                               "--confirm"], timeout=170)
            if cal_res.get("status") == "ok":
                msg += " · напоминание в календарь"
            else:
                msg += f" · календарь: {cal_res.get('error', '?')}"
        return {"status": res.get("status", "error"), "message": msg,
                "entry": res.get("entry"), "inventory": inv_result,
                "ad": ad_res, "olx": olx_auto_res, "calendar": cal_res}

    def _do_log_expense(self, p, platform, chat):
        desc = str(p.get("desc") or "").strip()
        amount = float(p.get("amount") or 0)
        if amount <= 0:
            return {"status": "error", "error": "Нужны desc и amount>0"}
        res = _finance().add("expense", amount, desc or "расход")
        return {"status": res.get("status", "error"), "message": f"Расход: {desc} = {amount} грн"}

    def _do_update_inventory(self, p, platform, chat):
        item = str(p.get("item") or "").strip()
        qty = int(p.get("qty_delta") or 0)
        price = p.get("price")
        if not item or qty == 0:
            return {"status": "error", "error": "Нужны item и qty_delta"}
        if qty > 0:
            res = _inventory().add(item, qty, float(price) if price else 0)
        else:
            res = _inventory().take(item, abs(qty))
        return {"status": res.get("status", "error"), "message": res.get("message") or str(res)}

    def _do_query_inventory(self, p, platform, chat):
        res = _inventory().stats() if hasattr(_inventory(), "stats") else {"status": "error"}
        items = _inventory()._load()
        return {"status": "ok", "message": f"Склад: {len(items)} позиций", "data": items[:20]}

    def _do_query_finance(self, p, platform, chat):
        rep = _finance().report(30)
        entries = _finance().listing(10).get("entries", [])
        return {"status": "ok", "message": f"Прибыль(30д): {rep.get('profit')} грн", "data": rep, "entries": entries}

    def _do_query_price_history(self, p, platform, chat):
        sku = str(p.get("sku") or p.get("item") or "").strip()
        return {"status": "ok", "message": f"История цен по «{sku or 'всем'}» из БД OLX",
                "data": self._price_history(sku)}

    def _do_query_np_status(self, p, platform, chat):
        ttn = str(p.get("ttn") or "").strip()
        if ttn:
            return _run_ac(["novaposhta", "track", ttn], timeout=90)
        return _run_ac(["novaposhta", "my_ttns"], timeout=90)

    # ---- Коммуникация ----
    def _do_reply_customer(self, p, platform, chat):
        text = str(p.get("text") or "").strip()
        if not text:
            return {"status": "error", "error": "Нет текста ответа"}
        if platform == "olx":
            return _run_ac(["olx", "chat", "reply", str(chat), text, "--confirm"], timeout=170)
        if platform == "instagram":
            return _run_ac(["instagram", "dm_send", str(chat), text], timeout=170)
        if platform == "facebook":
            return _run_ac(["facebook", "messenger_send", str(chat), text], timeout=170)
        if platform == "viber":
            return _run_ac(["viber", "send", str(chat), text], timeout=90)
        if platform == "telegram":
            return self._telegram_send(chat, text)
        return {"status": "error", "error": f"Не поддерживается отправка на {platform}"}

    def _do_query_platform(self, p, platform, chat):
        q = str(p.get("query") or "").strip()
        if platform == "olx":
            return _run_ac(["olx", "chat", "list"], timeout=170)
        if platform == "instagram":
            return _run_ac(["instagram", "dm_list", "6"], timeout=170)
        if platform == "facebook":
            return _run_ac(["facebook", "messenger_list", "--limit", "6"], timeout=170)
        if platform == "novaposhta":
            return _run_ac(["novaposhta", "my_ttns"], timeout=90)
        if platform == "abank":
            return _run_ac(["abank", "balance"], timeout=170)
        if platform == "privat":
            return _run_ac(["privat", "balance"], timeout=170)
        if platform == "abank_biz":
            return _run_ac(["abank_biz", "balance"], timeout=170)
        if platform == "privat_biz":
            return _run_ac(["privat_biz", "balance"], timeout=170)
        return {"status": "ok", "message": f"read-only {platform}: {q}"}

    # ---- Банки ----
    _BANKS = ("abank", "privat", "abank_biz", "privat_biz")

    def _do_bank_balance(self, p, platform, chat):
        bank = str(p.get("bank") or platform or "").strip()
        if bank not in self._BANKS:
            return {"status": "error", "error": "bank = " + " | ".join(self._BANKS)}
        return _run_ac([bank, "balance"], timeout=170)

    def _do_bank_transactions(self, p, platform, chat):
        bank = str(p.get("bank") or platform or "").strip()
        if bank not in self._BANKS:
            return {"status": "error", "error": "bank = " + " | ".join(self._BANKS)}
        return _run_ac([bank, "transactions"], timeout=170)

    def _do_bank_transfer(self, p, platform, chat):
        # Достигает сюда ТОЛЬКО после подтверждения владельца (guardrails MANUAL→approve)
        bank = str(p.get("bank") or platform or "").strip()
        if bank not in self._BANKS:
            return {"status": "error", "error": "bank = " + " | ".join(self._BANKS)}
        recipient = str(p.get("recipient") or "").strip()
        amount = p.get("amount")
        note = str(p.get("note") or "").strip()
        if not recipient or amount is None:
            return {"status": "error", "error": "Нужны recipient и amount"}
        return _run_ac([bank, "transfer", recipient, str(amount),
                        "--note", note, "--confirm"], timeout=170)

    # ---- Деактивация ----
    def _do_deactivate_ad(self, p, platform, chat):
        ad_id = str(p.get("ad_id") or "").strip()
        if not ad_id:
            return {"status": "error", "error": "Нет ad_id"}
        return _run_ac(["olx", "delete", ad_id, "--confirm"], timeout=170)

    # ---- ТТН и жизненный цикл продаж ----
    def _pending_for_ttn(self, item: str, platform: str, chat: str) -> dict:
        """Найти подходящую pending-сделку, не путая клиентов с одинаковым товаром."""
        try:
            path = Path(self.root) / "data" / "pending_sales.json"
            rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
            item_l = (item or "").casefold()
            preferred = [
                row for row in rows
                if row.get("status") == "pending"
                and str(row.get("platform") or "") == str(platform or "")
                and str(row.get("chat") or "") == str(chat or "")
                and (not item_l or str(row.get("item") or "").casefold() == item_l)
            ]
            if preferred:
                return preferred[-1]
            fallback = [
                row for row in rows
                if row.get("status") == "pending"
                and (not item_l or str(row.get("item") or "").casefold() == item_l)
            ]
            return fallback[-1] if fallback else {}
        except Exception:
            return {}

    def _do_create_ttn(self, p, platform, chat):
        """Создать ТТН после approval и сразу запустить lifecycle продажи."""
        # Достигает сюда только после подтверждения владельца (MANUAL → approve).
        item = str(p.get("item") or p.get("sku") or "").strip()
        pending = self._pending_for_ttn(item, platform, chat)
        item = item or str(pending.get("item") or "").strip()
        recipient = str(p.get("recipient") or pending.get("recipient") or "").strip()
        phone = str(p.get("phone") or pending.get("customer_phone") or "").strip()
        amount = p.get("amount")
        if amount is None:
            amount = pending.get("amount")
        address = str(p.get("address") or pending.get("delivery") or "").strip()
        city = str(p.get("city") or "").strip()
        warehouse = str(p.get("warehouse") or "").strip()
        if not city or not warehouse:
            try:
                from run_ttn import split_delivery
                parsed_city, parsed_warehouse = split_delivery(address)
                city = city or parsed_city
                warehouse = warehouse or parsed_warehouse
            except Exception:
                pass
        if not item or amount is None or not recipient or not phone or not city or not warehouse:
            return {
                "status": "error",
                "error": (
                    "Недостаточно данных для ТТН. Нужны товар, цена, ФИО, телефон, город и отделение. "
                    "Используйте: «создай ттн: товар, цена, ФИО, телефон, город, отделение»."
                ),
            }
        try:
            from run_ttn import create_ttn
            result = create_ttn(item, str(amount), recipient, phone, city, warehouse, confirm=True)
            if result.get("status") == "ok":
                lifecycle_message = result.get("sale_message") or "Товар зарезервирован, создана задача отправки."
                result["message"] = f"ТТН {result.get('ttn')} создана. {lifecycle_message}"
            return result
        except Exception as exc:
            return {"status": "error", "error": str(exc)[:200]}

    def _sales_lifecycle(self):
        from aios_core.sales_lifecycle import SalesLifecycle
        return SalesLifecycle(Path(self.root))

    @staticmethod
    def _sale_reference(params: dict) -> str:
        return str(params.get("reference") or params.get("ttn") or params.get("item") or "").strip()

    def _do_sale_tasks(self, p, platform, chat):
        rows = self._sales_lifecycle().list_open_tasks()
        if not rows:
            return {"status": "ok", "message": "Открытых задач по отправкам и возвратам нет.", "tasks": []}
        lines = ["Задачи по продажам:"]
        for row in rows[:12]:
            task, sale = row["task"], row["sale"]
            prefix = "принять возврат" if task.get("kind") == "return_receive" else "отправить"
            lines.append(f"• {prefix}: {sale.get('item')} · ТТН {sale.get('ttn') or '—'}")
        return {"status": "ok", "message": "\n".join(lines), "tasks": rows}

    def _do_mark_sale_shipped(self, p, platform, chat):
        return self._sales_lifecycle().mark_shipped(self._sale_reference(p), source="autonomy_owner")

    def _do_mark_sale_delivered(self, p, platform, chat):
        return self._sales_lifecycle().mark_delivered(self._sale_reference(p), source="autonomy_owner")

    def _do_mark_sale_returned(self, p, platform, chat):
        return self._sales_lifecycle().mark_returned(self._sale_reference(p), source="autonomy_owner")

    def _do_mark_return_received(self, p, platform, chat):
        return self._sales_lifecycle().mark_return_received(self._sale_reference(p), source="autonomy_owner")

    def _do_send_money(self, p, platform, chat):
        return {"status": "manual", "error": "Денежная операция — только вручную"}

    def _do_accept_advance(self, p, platform, chat):
        return {"status": "manual", "error": "Аванс — только вручную"}

    # ---- Автоподготовка сделки ----
    def _do_prepare_sale(self, p, platform, chat):
        """Зафиксировать намерение клиента купить (pending-сделка) — НЕ деньги, только запись."""
        item = str(p.get("item") or p.get("sku") or "").strip()
        amount = p.get("amount") or p.get("price")
        try:
            amount = float(amount) if amount else None
        except (TypeError, ValueError):
            amount = None
        delivery = str(p.get("delivery") or p.get("text") or "").strip()
        rec = {
            "ts": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
            "platform": platform,
            "chat": chat,
            "item": item or "",
            "amount": amount,
            "delivery": delivery[:200],
            "customer_phone": str(p.get("phone") or "").strip(),
            "recipient": str(p.get("recipient") or "").strip(),
            "status": "pending",
        }
        path = Path(self.root) / "data" / "pending_sales.json"
        try:
            data = []
            if path.exists():
                import json as _j
                data = _j.loads(path.read_text(encoding="utf-8"))
            data.append(rec)
            if len(data) > 50:
                data = data[-50:]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            # Уведомить владельца о новой сделке (для создания ТТН)
            try:
                self._notify_owner_sale(rec)
            except Exception:
                pass
            # Клиенту в чат должен идти вежливый ответ LLM (params.text), а не статус.
            reply_text = str(p.get("text") or "").strip()
            return {"status": "ok",
                    "message": reply_text or f"Сделка зафиксирована: {item or 'товар'}",
                    "sale": rec}
        except Exception as e:
            return {"status": "error", "error": str(e)[:150]}

    def _notify_owner_sale(self, rec: dict) -> None:
        """Отправить владельцу в Telegram уведомление о новой pending-сделке."""
        try:
            from . import _env
            token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
            chat_id = _env("TELEGRAM_CHAT_ID")
            if not (token and chat_id):
                return
            import urllib.request as _ur
            item = rec.get("item", "товар")
            amount = rec.get("amount")
            delivery = rec.get("delivery", "")
            txt = (f"🤝 <b>Новая сделка (готово к отправке)</b>\n"
                   f"Площадка: {rec.get('platform')} · клиент: {rec.get('chat')}\n"
                   f"Товар: <b>{item}</b>\n"
                   f"Цена: {amount} грн\n"
                   f"Доставка: {delivery or '—'}\n"
                   f"Создать ТТН: «создай ттн {item} ...» или вручную")
            payload = {"chat_id": int(chat_id), "text": txt[:3800],
                       "parse_mode": "HTML", "disable_web_page_preview": True}
            req = _ur.Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"})
            with _ur.urlopen(req, timeout=60):
                pass
        except Exception:
            pass
        except Exception as e:
            return {"status": "error", "error": str(e)[:150]}

    def _do_pending_sales(self, p, platform, chat):
        """Список pending-сделок (для владельца)."""
        path = Path(self.root) / "data" / "pending_sales.json"
        try:
            import json as _j
            data = _j.loads(path.read_text(encoding="utf-8")) if path.exists() else []
            return {"status": "ok", "sales": data, "count": len(data)}
        except Exception as e:
            return {"status": "error", "error": str(e)[:150]}

    def _do_create_ad(self, p, platform, chat):
        # Владелец подтвердил — создаём объявление на OLX через run_olx_ad_gen.
        title = str(p.get("title") or "").strip()
        desc = str(p.get("desc") or "").strip()
        price = p.get("price")
        # если не хватает данных — попробовать взять из склада по item
        if not title or not price:
            item = str(p.get("item") or "").strip()
            inv = _inventory()._find(_inventory()._load(), item) if item else None
            if inv:
                title = title or inv.get("name", "")
                price = price or inv.get("price", 0)
                if not desc:
                    desc = f"Продам {inv.get('name')}. Цена {price} грн."
        if not title:
            return {"status": "error", "error": "Нужен title (или item из склада)"}
        try:
            import subprocess as _sp
            py = PY
            cmd = [py, str(self.root / "run_olx_ad_gen.py"), "create", title, "--confirm"]
            r = _sp.run(cmd, capture_output=True, text=True, timeout=220, cwd=str(self.root))
            out = (r.stdout or "").strip()
            start = out.find("{")
            if start >= 0:
                return json.loads(out[start:])
            return {"status": "ok", "message": out[-300:] or "объявление создано"}
        except Exception as e:
            return {"status": "error", "error": str(e)[:200]}

    def _do_boost_ad(self, p, platform, chat):
        return {"status": "manual", "error": "Буст объявления — только с подтверждением"}

    def _do_publish(self, p, platform, chat):
        return {"status": "manual", "error": "Публикация — только с подтверждением"}

    # ---- helpers ----
    def _price_history(self, sku: str):
        try:
            import sqlite3
            conn = sqlite3.connect(str(self.root / "data" / "olx_http.sqlite"))
            cur = conn.execute(
                "SELECT title, price_value, url FROM ads WHERE active=1 "
                "AND (?='' OR title LIKE '%'||?||'%') ORDER BY price_value LIMIT 10",
                (sku, sku))
            rows = [{"title": r[0], "price": r[1], "url": r[2]} for r in cur.fetchall()]
            conn.close()
            return rows
        except Exception:
            return []

    def _telegram_send(self, chat_id, text):
        try:
            import urllib.request
            from . import _env
            token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
            if not token:
                return {"status": "error", "error": "нет TELEGRAM_BOT_TOKEN"}
            payload = {"chat_id": int(chat_id), "text": text[:3800],
                       "parse_mode": "HTML", "disable_web_page_preview": True}
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60):
                pass
            return {"status": "ok", "message": "отправлено в Telegram"}
        except Exception as e:
            return {"status": "error", "error": str(e)[:200]}
