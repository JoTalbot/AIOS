"""Sales Lifecycle intent (выделено из run_telegram_bot.py).

Детерминированная обработка статусов продаж: CRM, задачи отправки,
«отправил ТТН», «доставлено ТТН», возвраты.
"""
from __future__ import annotations

import re
from pathlib import Path

from tg_bot.common import _esc_tg

PROJECT_ROOT = Path(__file__).resolve().parent.parent


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
