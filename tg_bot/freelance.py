"""Freelance intent (выделено из run_telegram_bot.py).

Команды владельца: «подтверди фриланс <id>», «список фриланса»,
«инвойс фриланс <id>» — подтверждение оплаты, список решённых задач, инвойсы.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from tg_bot.common import _esc_tg

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _handle_freelance_intent(api, chat_id: int, text: str) -> bool:
    """Обрабатывает фриланс-команды владельца.
    Команды:
      «подтверди фриланс <task_id>» или «confirm freelance <task_id>» — подтверждает оплату за выполненную задачу и зачисляет деньги в 4 кошелька.
      «список фриланса» или «фриланс список» — выводит список решенных задач, ожидающих подтверждения оплаты.
      «инвойс фриланс <task_id>» или «invoice freelance <task_id>» — генерирует и отправляет интерактивный HTML-инвойс для этой задачи.
    """
    import re as _re3
    t = " ".join(str(text or "").casefold().split())

    # 1. Обработка подтверждения оплаты
    approve = _re3.match(r"^(?:подтверди\s+фриланс|подтвердить\s+фриланс|confirm\s+freelance)\s+(\S+)", t)
    if approve:
        task_id = approve.group(1).strip()
        tasks_file = PROJECT_ROOT / "data" / "freelance_tasks.json"
        if not tasks_file.exists():
            api.send_message(chat_id, "⚠️ Файл задач фриланса не найден.")
            return True

        try:
            tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
        except Exception as e:
            api.send_message(chat_id, f"⚠️ Ошибка чтения файла задач: {e}")
            return True

        target_task = None
        for task in tasks:
            if task.get("id") == task_id:
                target_task = task
                break

        if not target_task:
            api.send_message(chat_id, f"❌ Задача с ID <code>{task_id}</code> не найдена.")
            return True

        if target_task.get("status") == "PAID":
            api.send_message(chat_id, f"ℹ️ Оплата по задаче <code>{task_id}</code> уже была зачислена ранее.")
            return True

        # Зачисляем реальный доход в кошелек системы
        from aios_core.crypto_wallet import AIOSWalletManager
        wallet = AIOSWalletManager(str(PROJECT_ROOT / "data"))

        try:
            budget = float(target_task.get("budget_usd", 0.0))
            source = f"Freelance:{target_task.get('source', 'unknown')}"

            # Начисляем и делим на 4 кошелька
            wallet.record_income(
                amount_usd=budget,
                source=source,
                task_id=task_id
            )

            # Меняем статус на PAID
            target_task["status"] = "PAID"
            tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")

            # Составляем сообщение без f-string с literal newlines
            txt = "✅ <b>Оплата фриланса зачислена!</b>\\n\\n"
            txt += "ID: <code>" + task_id + "</code>\\n"
            txt += "Задача: <i>" + str(target_task.get('title', '')) + "</i>\\n"
            txt += "Сумма: <b>$" + f"{budget:.2f}" + " USD</b>\\n\\n"
            txt += "Бюджет распределен по 25% ($" + f"{budget*0.25:.2f}" + " каждому): Разработчик, Инвестор, Персонал, Система."

            api.send_message(chat_id, txt)
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка при фиксации оплаты: {e}")

        return True

    # 2. Обработка просмотра списка
    if any(phrase in t for phrase in ("список фриланса", "фриланс список", "фриланс задачи", "ожидают оплаты")):
        tasks_file = PROJECT_ROOT / "data" / "freelance_tasks.json"
        if not tasks_file.exists():
            api.send_message(chat_id, "📭 Фриланс-задач нет.")
            return True

        try:
            tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
        except Exception:
            api.send_message(chat_id, "⚠️ Ошибка чтения файла задач.")
            return True

        pending = [t for t in tasks if t.get("status") == "BID_SUBMITTED"]
        if not pending:
            api.send_message(chat_id, "📭 Нет фриланс-задач, ожидающих подтверждения оплаты.")
            return True

        lines = [f"📋 <b>Фриланс-задачи в работе (ожидают оплаты): {len(pending)}</b>"]
        for task in pending[-15:]:
            lines.append(
                f"• ID: <code>{task.get('id')}</code>\\n"
                f"  <i>{task.get('title')}</i>\\n"
                f"  Бюджет: <b>${task.get('budget_usd')} USD</b> (Источник: {task.get('source')})\\n"
                f"  Инвойс: <code>инвойс фриланс {task.get('id')}</code>\\n"
                f"  Подтвердить оплату: <code>подтверди фриланс {task.get('id')}</code>"
            )
        api.send_message(chat_id, "\\n\\n".join(lines)[:4000])
        return True

    # 3. Обработка получения инвойса
    get_inv = _re3.match(r"^(?:инвойс\s+фриланс|invoice\s+freelance)\s+(\S+)", t)
    if get_inv:
        task_id = get_inv.group(1).strip()
        tasks_file = PROJECT_ROOT / "data" / "freelance_tasks.json"
        if not tasks_file.exists():
            api.send_message(chat_id, "⚠️ Файл задач фриланса не найден.")
            return True

        try:
            tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
        except Exception:
            api.send_message(chat_id, "⚠️ Ошибка чтения файла задач.")
            return True

        target_task = None
        for task in tasks:
            if task.get("id") == task_id:
                target_task = task
                break

        if not target_task:
            api.send_message(chat_id, f"❌ Задача с ID <code>{task_id}</code> не найдена.")
            return True

        api.send_message(chat_id, "📊 <b>Генерирую интерактивный счет для задачи...</b>")
        from aios_core.invoice_generator import AIOSInvoiceGenerator
        invoicer = AIOSInvoiceGenerator(str(PROJECT_ROOT / "data"))
        try:
            invoice_path = invoicer.generate_invoice_html(
                client_name=target_task.get("source", "unknown"),
                amount_usd=float(target_task.get("budget_usd", 0.0)),
                service_desc=target_task.get("title", ""),
                invoice_id=task_id
            )
            api.send_document(chat_id, invoice_path, caption=f"📑 Инвойс № {task_id} · {target_task.get('source')}")
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка выписки счета: {e}")
        return True

    return False



























































# ---------------------------------------------------------------------------
# Coder commands — MetaCognitiveCoder integration
# ---------------------------------------------------------------------------


_coder_mod = None

