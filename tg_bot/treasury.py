"""Крипто-казначейство, Kraken, фиат, invoice, ончейн (выделено из run_telegram_bot.py)."""
from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from tg_bot.common import PROJECT_ROOT, _esc_tg


def _handle_treasury_intent(api, chat_id: int, text: str) -> bool:
    """Обрабатывает команды казначейства, реинвестирования, биржи Kraken, SRE мониторинга и вывода в фиат.
    Команды:
      «казначейство» или «баланс казначейства» — выводит аудит казначейства, резерв и излишки.
      «реинвестируй <сумма>» — запускает реальный On-Chain депозит в Aave V3 Polygon.
      «верни из дефи <сумма>» или «withdraw defi <сумма>» — запускает реальный On-Chain вывод из Aave V3 Polygon.
      «финансовый отчет» или «отчет по финансам» — генерирует и отправляет профессиональный отчет в формате Excel (.xlsx).
      «ставки дефи» или «доходность дефи» — запрашивает и выводит процентные ставки в Aave и Compound.
      «баланс кракен» или «кракен баланс» — выводит реальный баланс активов на вашем аккаунте Kraken.
      «купи на кракене <пара> <объем>» — исполняет реальный рыночный ордер покупки на Kraken.
      «продай на кракене <пара> <объем>» — исполняет реальный рыночный ордер продажи на Kraken.
      «статус служб» или «девопс статус» — запускает активное HTTP-зондирование всех веб-служб системы (SRE).
      «выведи <сумма> usdt на карту <номер_карты>» — инициирует ордер обмена крипты в фиатные гривны и вывод на карту!
      «сканируй ошибки» или «sre healer» — сканирует лог на наличие трейсбеков Python.
      «исправь ошибку» или «sre heal» — запускает ИИ для автоматического исправления последнего бага в коде.
    """
    import re as _re4
    t = " ".join(str(text or "").casefold().split())

    # Смарт-маршрутизатор ликвидности (v19.0.0)
    if any(phrase in t for phrase in ("ликвидность", "смарт ликвидность", "маршрутизатор", "доходность сетей", "кросс-чейн")):
        api.send_message(chat_id, "🌐 <b>Запрашиваю мульти-чейн анализ доходностей DeFi v19.1...</b>")
        import subprocess as _sp_lr
        try:
            r = _sp_lr.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_smart_liquidity_router.py"), "--telegram"],
                           capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
            # v19.1 --telegram outputs markdown directly
            report = r.stdout.strip()
            if report:
                api.send_message(chat_id, report)
            else:
                import json as _j_lr
                data = _j_lr.loads(r.stdout)
                best = data.get("best_yield_strategy", {})
                lines = [
                    "🌐 <b>AIOS Smart Liquidity Router v19.1:</b>\n",
                    f"🥇 <b>Лучшая стратегия:</b> {best.get('protocol')} на <b>{best.get('network')}</b> ({best.get('asset')})",
                    f"• Доходность: <b>{best.get('apy_pct')}% APY</b>\n",
                    "📊 <b>Все доступные пулы:</b>"
                ]
                for opp in data.get("all_opportunities", []):
                    lines.append(f"• <b>{opp.get('network')}</b> ({opp.get('protocol')}): <b>{opp.get('apy_pct')}% APY</b> [{opp.get('asset')}]")
                lines.append(f"\n💰 Доступно излишков: <b>${data.get('available_excess_capital_usd', 0.0):.2f}</b>")
                lines.append(f"📈 Прогноз: <b>+${data.get('estimated_annual_yield_usd', 0.0):.2f}/год</b>")
                if data.get("rebalance_action_required"):
                    q = data.get("bridge_quote", {})
                    lines.append(f"\n🟢 Ребаланс {data.get('current_network')}→{best.get('network')} net +${data.get('net_gain_annual_usd',0)} после fee ${q.get('total_fee_usd',0)}")
                api.send_message(chat_id, "\n".join(lines))
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка анализа ликвидности v19.1: {e}")
        return True

    # Сканер арбитража DEX & CEX v19.2 (cross-DEX)
    if any(phrase in t for phrase in ("арбитраж", "спред", "dex арбитраж", "разница цен", "⚡ арбитраж")):
        api.send_message(chat_id, "🔎 <b>Сканирую кросс-DEX/CEX арбитраж v19.2 (Kraken/Binance/CG/UniV3)...</b>")
        import subprocess as _sp_arb
        try:
            r = _sp_arb.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_dex_arbitrage_scanner.py"), "--cross", "--telegram"],
                            capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
            report = r.stdout.strip()
            if report:
                api.send_message(chat_id, report)
            else:
                import json as _j_arb
                data = _j_arb.loads(r.stdout)
                lines = ["📊 <b>AIOS DEX/CEX Arbitrage Radar v19.2:</b>\n"]
                for opp in data.get("opportunities", []):
                    lines.append(
                        f"• <b>{opp.get('pair')}</b> ({opp.get('exchange')}):\n"
                        f"  Bid: ${opp.get('bid'):.2f} | Ask: ${opp.get('ask'):.2f}\n"
                        f"  Спред: <b>${opp.get('spread_usd')}</b> ({opp.get('spread_pct')}%) — 🟢 {opp.get('opportunity')}"
                    )
                api.send_message(chat_id, "\n".join(lines))
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка сканера арбитража v19.2: {e}")
        return True


    # Android Mesh v19.3
    if any(phrase in t for phrase in ("mesh", "меш", "📱 mesh", "android mesh", "fleet", "флот")):
        api.send_message(chat_id, "📱 <b>Запрашиваю статус Android Mesh v19.3...</b>")
        import subprocess as _sp_mesh
        try:
            r = _sp_mesh.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_android_mesh.py"), "--telegram"],
                            capture_output=True, text=True, timeout=15, cwd=str(PROJECT_ROOT))
            report = r.stdout.strip()
            if report:
                api.send_message(chat_id, report)
            else:
                api.send_message(chat_id, "❌ Пустой отчет Mesh")
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка Android Mesh: {e}")
        return True

    # 0. Сброс демонстрационного счёта Kraken ($100)
    if any(phrase in t for phrase in ("сбрось демо", "сбросить демо", "кракен демо сброс", "сбросить демо кракен", "сброс демо")):
        from aios_core.quant_trading_engine import reset_kraken_demo_account
        if reset_kraken_demo_account():
            api.send_message(chat_id, "✅ <b>Демонстрационный счёт Kraken успешно сброшен на $100.00 USD!</b>")
        else:
            api.send_message(chat_id, "❌ Не удалось сбросить демонстрационный счёт Kraken.")
        return True

    # Трейдинг, Демо-счёт $100 Kraken и процесс заработка
    if any(phrase in t for phrase in (
        "трейдинг", "сигналы", "квант", "торговля", "paper trading",
        "демо счет", "демосчет", "демо счёт", "демо кракен", "кракен демо",
        "заработок кракен", "кракен заработок", "кракен трейдинг", "демо"
    )):
        api.send_message(chat_id, "🐙 <b>Запрашиваю показатели демонстрационного счёта Kraken ($100)...</b>")
        try:
            from aios_core.quant_trading_engine import (
                get_kraken_demo_report,
                format_kraken_demo_report,
                QuantMasterOrchestrator
            )
            try:
                quant = QuantMasterOrchestrator()
                quant.run_quant_cycle()
            except Exception:
                pass

            report = get_kraken_demo_report()
            msg_text = format_kraken_demo_report(report)
            api.send_message(chat_id, msg_text)
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка получения данных демо-счёта Kraken: {e}")
        return True

    # Склад & Запчасти
    if any(phrase in t for phrase in ("склад & olx", "склад", "остатки на складе", "инвентарь")):
        import subprocess as _sp_inv
        try:
            r = _sp_inv.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_inventory.py"), "stats"],
                           capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
            import json as _j_inv
            data = _j_inv.loads(r.stdout)
            lines = [
                "🛒 <b>Склад запчастей AIOS:</b>\n",
                f"• Всего наименований: <b>{data.get('items_count', 0)}</b>",
                f"• Доступно деталей: <b>{data.get('available_qty', 0)} шт</b>",
                f"• В резерве: <b>{data.get('reserved_qty', 0)} шт</b>",
                f"• Оценочная стоимость: <b>{data.get('total_value', 0)} грн</b>\n",
                "Для добавления детали напишите:\n<code>склад добавить <название> <цена> <кол-во></code>"
            ]
            api.send_message(chat_id, "\n".join(lines))
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка склада: {e}")
        return True


    # Публичный веб-каталог и витрина
    if any(phrase in t for phrase in ("веб-каталог", "веб каталог", "каталог", "витрина", "сайт", "ссылка на склад")):
        lines = [
            "🌐 <b>Онлайн-каталог автозапчастей AIOS:</b>\n",
            "🔗 <b>Ссылка для клиентов:</b>",
            "https://api.autosklo.org.ua/parts/\n",
            "📦 <b>Что доступно на витрине:</b>",
            "• Авторазборка ВАЗ (Лада) 2108–2115 (от 100 грн)",
            "• Авторазборка ГАЗель 3302, Соболь, Рута (от 200 грн)",
            "• Радиатор охлаждения ВАЗ 2109 (950 грн)",
            "• Рессора задняя ГАЗель 3302 5-лист. (1 800 грн)",
            "• Генератор ВАЗ 2110 80А (1 400 грн)\n",
            "<i>Отправьте эту ссылку клиенту для просмотра фото и быстрого заказа!</i>"
        ]
        api.send_message(chat_id, "\n".join(lines))
        return True


    # Авто-экстракция реквизитов доставки из чата клиента (AI Order Extractor)
    if any(phrase in t for phrase in ("извлеки заказ", "парсинг доставки", "извлечь адрес", "распознай адрес", "извлеки адрес")) or ("отделение" in t and any(k in t for k in ("получатель", "тел", "г.", "город"))):
        api.send_message(chat_id, "🤖 <b>ИИ анализирует реквизиты доставки клиента...</b>")
        from aios_core.order_extractor import AIOSOrderExtractor
        extractor = AIOSOrderExtractor()
        try:
            res = extractor.extract_delivery_details(text)
            data = res.get("extracted_data", {})
            lines = [
                "📦 <b>ИИ извлек данные для Новой Почты:</b>\n",
                f"• Товар: <b>{data.get('part_name') or 'Автозапчасть'}</b>",
                f"• Получатель: <b>{data.get('recipient_name') or 'Не указан'}</b>",
                f"• Телефон: <b>{data.get('phone') or 'Не указан'}</b>",
                f"• Город: <b>{data.get('city') or 'Не указан'}</b>",
                f"• Отделение: <b>{data.get('warehouse') or '1'}</b>",
                f"• Оплата: <i>{data.get('payment_type') or 'наложенный платеж'}</i>\n",
                "🚀 <b>Готовая команда создания ТТН (скопируйте и отправьте):</b>",
                f"<code>{res.get('generated_ttn_command')}</code>"
            ]
            api.send_message(chat_id, "\n".join(lines))
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка извлечения заказа: {e}")
        return True

    # Новая Почта
    if any(phrase in t for phrase in ("новая почта", "создать ттн", "накладная нп", "почта")):
        import subprocess as _sp_np
        try:
            r = _sp_np.run(["/opt/aios/.venv/bin/python", str(PROJECT_ROOT / "run_ttn.py"), "whoami"],
                           capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))
            import json as _j_np
            data = _j_np.loads(r.stdout)
            sender = data.get("sender", {})
            contact = sender.get("contact_desc", "Приватна особа")
            lines = [
                "📦 <b>Логистика Новая Почта:</b>\n",
                f"• Отправитель API: <b>{contact}</b>",
                "• Статус ключа: 🟢 <b>Подключен</b>\n",
                "<b>Команды логистики:</b>",
                "• Поиск города: <code>город Киев</code>",
                "• Поиск отделений: <code>отделения Киев 1</code>",
                "• Создать ТТН: <code>создай ТТН: <Деталь>, <Цена>, <ФИО>, <Телефон>, <Город>, <Отделение></code>"
            ]
            api.send_message(chat_id, "\n".join(lines))
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка Новой Почты: {e}")
        return True


    # 1. Запрос баланса и аудита
    if any(phrase in t for phrase in ("казначейство", "баланс казначейства", "резерв системы", "аудит казначейства")):
        from aios_core.treasury_manager import AIOSTreasuryManager
        manager = AIOSTreasuryManager()
        try:
            audit = manager.audit_reserves()
            lines = [
                "💰 <b>Казначейство и Резервы AIOS:</b>\n",
                f"• Автономный бюджет Системы: <b>${audit['system_budget_usd']:.2f} USD</b>",
                f"• Месячные расходы: <b>${audit['monthly_operating_cost_usd']:.2f} USD</b>",
                f"• Буфер выживаемости (3 мес): <b>${audit['safety_buffer_3_months_usd']:.2f} USD</b>",
                f"• Доступно для реинвестирования: <b>${audit['excess_funds_available_usd']:.2f} USD</b>",
                f"• Активный депозит в Aave V3: <b>${audit['active_aave_deposit_usd']:.2f} USD</b>\n"
            ]
            if audit["reinvestment_recommended"]:
                lines.append(f"🟢 Рекомендуется реинвестировать излишки в DeFi!\\nДля запуска напишите: <code>реинвестируй {int(audit['excess_funds_available_usd'])}</code>")
            else:
                lines.append("ℹ️ Свободных средств пока недостаточно для реинвестирования (нужно > $10).")

            api.send_message(chat_id, "\n".join(lines))
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка аудита казначейства: {e}")
        return True

    # 2. Команда реинвестирования
    reinvest = _re4.match(r"^(?:реинвестируй|реинвестировать|reinvest)\s+([0-9]+(?:\.[0-9]+)?)", t)
    if reinvest:
        amount = float(reinvest.group(1))
        if amount < 1.0:
            api.send_message(chat_id, "❌ Минимальная сумма для реинвестирования — $1.00 USD.")
            return True

        api.send_message(chat_id, f"📡 <b>Инициирован On-Chain депозит в Aave V3: ${amount:.2f} USDT...</b>\\n\\nПроверяю балансы, выполняю Approve и Supply на Polygon...")

        from aios_core.treasury_manager import AIOSTreasuryManager
        manager = AIOSTreasuryManager()
        try:
            # Сверяем излишки
            audit = manager.audit_reserves()
            if audit["system_budget_usd"] < amount:
                api.send_message(chat_id, f"❌ Недостаточно средств в бюджете системы: доступно ${audit['system_budget_usd']:.2f}, затребовано ${amount:.2f}.")
                return True

            # Запуск On-Chain транзакции!
            res = manager.execute_aave_reinvestment(amount)
            if res.get("status") == "success":
                txt = "✅ <b>Депозит в Aave V3 успешно выполнен!</b>\\n\\n"
                txt += "Сумма: <b>$" + f"{amount:.2f}" + " USDT</b> (Сеть Polygon)\\n"
                if res.get("approve_tx_hash"):
                    txt += "• TxHash Approve: <code>" + res.get("approve_tx_hash") + "</code>\\n"
                txt += "• TxHash Supply: <code>" + res.get("supply_tx_hash") + "</code>\\n\\n"
                txt += "Пассивный доход в стейблкоинах теперь зачисляется на кошелек казначейства каждую секунду!"
                api.send_message(chat_id, txt)
            else:
                api.send_message(chat_id, f"❌ Ошибка реинвестирования: {res.get('error')}")
        except Exception as e:
            api.send_message(chat_id, f"❌ Критическая ошибка Web3: {e}")

        return True

    # 3. Команда вывода из Aave
    withdraw = _re4.match(r"^(?:верни\s+из\s+дефи|верни\s+из\s+defi|withdraw\s+defi)\s+([0-9]+(?:\.[0-9]+)?)", t)
    if withdraw:
        amount = float(withdraw.group(1))
        if amount < 1.0:
            api.send_message(chat_id, "❌ Минимальная сумма для вывода — $1.00 USD.")
            return True

        api.send_message(chat_id, f"📡 <b>Инициирован вывод из Aave V3: ${amount:.2f} USDT...</b>\\n\\nВывожу стейблкоины на горячий кошелек системы на Polygon...")

        from aios_core.treasury_manager import AIOSTreasuryManager
        manager = AIOSTreasuryManager()
        try:
            # Сверяем баланс депозита перед отправкой
            audit = manager.audit_reserves()
            if audit["active_aave_deposit_usd"] < amount:
                api.send_message(chat_id, f"❌ Недостаточно средств на депозите Aave V3: доступно ${audit['active_aave_deposit_usd']:.2f}, затребовано ${amount:.2f}.")
                return True

            # Запуск On-Chain транзакции!
            res = manager.execute_aave_withdrawal(amount)
            if res.get("status") == "success":
                txt = "✅ <b>Вывод из Aave V3 успешно выполнен!</b>\\n\\n"
                txt += "Сумма: <b>$" + f"{amount:.2f}" + " USDT</b> (Сеть Polygon)\\n"
                txt += "• TxHash: <code>" + res.get("tx_hash") + "</code>\\n\\n"
                txt += "Средства зачислены обратно на горячий кошелек и доступны для расходов."
                api.send_message(chat_id, txt)
            else:
                api.send_message(chat_id, f"❌ Ошибка вывода: {res.get('error')}")
        except Exception as e:
            api.send_message(chat_id, f"❌ Критическая ошибка Web3: {e}")

        return True

    # 4. Запрос Excel отчета
    if any(phrase in t for phrase in ("финансовый отчет", "отчет по финансам", "скачать отчет", "экспорт финансов")):
        api.send_message(chat_id, "📊 <b>Инициирована генерация финансового отчета Excel...</b>")
        from aios_core.accounting_reporter import AIOSAccountingReporter
        reporter = AIOSAccountingReporter()
        try:
            report_path = reporter.generate_excel_report()
            api.send_document(chat_id, report_path, caption="📊 Финансовый отчет AIOS (.xlsx) · Обновляется автономно")
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка генерации финансового отчета: {e}")
        return True

    # 5. Запрос ставок DeFi
    if any(phrase in t for phrase in ("ставки дефи", "дефи ставки", "доходность дефи", "defi доходность", "проценты дефи")):
        api.send_message(chat_id, "📡 <b>Запрашиваю процентные ставки в DeFi ...</b>")
        from aios_core.treasury_manager import AIOSTreasuryManager
        manager = AIOSTreasuryManager()
        try:
            rates = manager.check_defi_yields()
            strategy = rates["best_yield_strategy"]
            lines = [
                "📊 <b>Текущие ставки доходности (Lending APY):</b>\n",
                f"• Polygon Aave V3 (USDT): <b>{rates['polygon_aave_v3_usdt_apy']:.2f}% APY</b>",
                f"• Base Compound V3 (USDC): <b>{rates['base_compound_v3_usdc_apy']:.2f}% APY</b>\n",
                f"⭐ <b>Лучшая стратегия:</b>",
                f"Используем протокол <b>{strategy['protocol']}</b> в сети <b>{strategy['network']}</b> с доходностью <b>{strategy['apy']:.2f}% APY</b>."
            ]
            api.send_message(chat_id, "\n".join(lines))
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка запроса ставок: {e}")
        return True

    # 6. Запрос баланса Kraken
    if any(phrase in t for phrase in ("баланс кракен", "кракен баланс", "баланс на кракене", "активы кракен")):
        api.send_message(chat_id, "🔎 <b>Запрашиваю реальные балансы на бирже Kraken...</b>")
        from aios_core.kraken_client import AIOSKrakenClient
        client = AIOSKrakenClient()
        try:
            res = client.get_account_balance()
            if res.get("status") == "success":
                balances = res.get("balances", {})
                if not balances:
                    api.send_message(chat_id, "ℹ️ <b>Kraken:</b> Балансы всех активов в данный момент равны нулю (аккаунт пуст).")
                else:
                    lines = ["💰 <b>Реальные балансы на аккаунте Kraken:</b>\n"]
                    for asset, val in balances.items():
                        lines.append(f"• {asset}: <b>{val:.6f}</b>")
                    api.send_message(chat_id, "\n".join(lines))
            else:
                api.send_message(chat_id, f"❌ Ошибка запроса баланса: {res.get('error')}")
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка подключения к бирже: {e}")
        return True

    # 7. Ордер покупки на Kraken
    buy_order = _re4.match(r"^(?:купи\\s+на\\s+кракене|buy\\s+on\\s+kraken)\\s+(\\S+)\\s+([0-9]+(?:\\.[0-9]+)?)\\b", t)
    if buy_order:
        pair = buy_order.group(1).upper()
        volume = float(buy_order.group(2))

        api.send_message(chat_id, f"🚀 <b>Исполняю реальный ордер ПОКУПКИ на Kraken: {volume} {pair}...</b>")

        from aios_core.kraken_client import AIOSKrakenClient
        client = AIOSKrakenClient()
        try:
            res = client.add_market_order(pair, "buy", volume)
            if res.get("status") == "success":
                txt = "✅ <b>Рыночный ордер ПОКУПКИ успешно исполнен!</b>\\n\\n"
                txt += f"• Пара: <b>{pair}</b>\\n"
                txt += f"• Объем: <b>{volume}</b>\\n"
                txt += f"• Описание: <i>{res.get('description')}</i>\\n"
                txt += f"• ID Сделки: <code>{', '.join(res.get('tx_ids', []))}</code>"
                api.send_message(chat_id, txt)
            else:
                api.send_message(chat_id, f"❌ Ошибка исполнения ордера: {res.get('error')}")
        except Exception as e:
            api.send_message(chat_id, f"❌ Критическая ошибка API: {e}")
        return True

    # 8. Ордер продажи на Kraken
    sell_order = _re4.match(r"^(?:продай\\s+на\\s+кракене|sell\\s+on\\s+kraken)\\s+(\\S+)\\s+([0-9]+(?:\\.[0-9]+)?)\\b", t)
    if sell_order:
        pair = sell_order.group(1).upper()
        volume = float(sell_order.group(2))

        api.send_message(chat_id, f"🚀 <b>Исполняю реальный ордер ПРОДАЖИ на Kraken: {volume} {pair}...</b>")

        from aios_core.kraken_client import AIOSKrakenClient
        client = AIOSKrakenClient()
        try:
            res = client.add_market_order(pair, "sell", volume)
            if res.get("status") == "success":
                txt = "✅ <b>Рыночный ордер ПРОДАЖИ успешно исполнен!</b>\\n\\n"
                txt += f"• Пара: <b>{pair}</b>\\n"
                txt += f"• Объем: <b>{volume}</b>\\n"
                txt += f"• Описание: <i>{res.get('description')}</i>\\n"
                txt += f"• ID Сделки: <code>{', '.join(res.get('tx_ids', []))}</code>"
                api.send_message(chat_id, txt)
            else:
                api.send_message(chat_id, f"❌ Ошибка исполнения ордера: {res.get('error')}")
        except Exception as e:
            api.send_message(chat_id, f"❌ Критическая ошибка API: {e}")
        return True

    # 9. Запрос статуса SRE
    if any(phrase in t for phrase in ("статус служб", "девопс статус", "sre статус", "здоровье служб")):
        api.send_message(chat_id, "🔎 <b>Запускаю активное HTTP-зондирование веб-служб системы (SRE)...</b>")
        from aios_core.web_administrator import AIOSWebAdministrator
        admin = AIOSWebAdministrator()
        try:
            probes = admin.probe_services()
            lines = ["🛡️ <b>SRE-Статус веб-сервисов AIOS:</b>\n"]
            for p in probes:
                status_icon = "🟢" if p["is_healthy"] else "🔴"
                lines.append(
                    f"{status_icon} <b>{p['service_name']}</b>\n"
                    f"  • URL: <code>{p['url']}</code>\n"
                    f"  • HTTP Код: <b>{p['status_code']}</b> | Latency: <b>{p['latency_seconds']:.3f}с</b>"
                )
                if p["error"]:
                    lines.append(f"  • Ошибка: <i>{p['error']}</i>")

            api.send_message(chat_id, "\n\n".join(lines))
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка DevOps-мониторинга: {e}")
        return True

    # 10. Команда вывода в фиат на банковскую карту
    fiat_order = _re4.match(r"^(?:выведи|вывести|withdraw\\s+card)\\s+([0-9]+(?:\\.[0-9]+)?)\\s+usdt\\s+(?:на\\s+карту|на\\s+card|to\\s+card)\\s+([0-9]{16})\\b", t)
    if fiat_order:
        amount_usdt = float(fiat_order.group(1))
        card_number = fiat_order.group(2)

        api.send_message(chat_id, f"📡 <b>Запрашиваю курс обмена и создаю инвойс...</b>")
        from aios_core.fiat_dispatcher import AIOSFiatDispatcher
        dispatcher = AIOSFiatDispatcher()
        try:
            rate_info = dispatcher.get_fiat_exchange_rate(amount_usdt)
            expected_uah = rate_info["expected_amount_uah"]
            rate = rate_info["estimated_rate"]

            alert_state_file = PROJECT_ROOT / "data" / "fiat_withdrawal_pending.json"
            alert_state_file.write_text(json.dumps({
                "amount_usdt": amount_usdt,
                "card_number": card_number,
                "expected_uah": expected_uah,
                "timestamp": time.time()
            }), encoding="utf-8")

            txt = f"📡 <b>Курс обмена зафиксирован!</b>\\n\\n"
            txt += f"• Курс: <b>1 USDT = {rate:.2f} UAH</b>\\n"
            txt += f"• Вы получите: <b>{expected_uah:.2f} UAH</b>\\n"
            txt += f"• Карта зачисления: <code>{card_number[:4]} **** **** {card_number[-4:]}</code>\\n\\n"
            txt += "Для подтверждения On-Chain отправки напишите: <code>подтверди вывод на карту</code>"
            api.send_message(chat_id, txt)
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка создания ордера обмена: {e}")
        return True

    # 11. Подтверждение вывода в фиат
    if any(phrase in t for phrase in ("подтверди вывод на карту", "подтвердить вывод на карту", "confirm withdraw card")):
        pending_file = PROJECT_ROOT / "data" / "fiat_withdrawal_pending.json"
        if not pending_file.exists():
            api.send_message(chat_id, "❌ Нет активных запросов на вывод средств на карту.")
            return True

        try:
            pend_data = json.loads(pending_file.read_text(encoding="utf-8"))
            amount_usdt = float(pend_data["amount_usdt"])
            card_number = pend_data["card_number"]

            api.send_message(chat_id, f"🚀 <b>Исполняю On-Chain перевод ${amount_usdt:.2f} USDT на обменный адрес...</b>")

            from aios_core.fiat_dispatcher import AIOSFiatDispatcher
            dispatcher = AIOSFiatDispatcher()
            res = dispatcher.execute_fiat_withdrawal(amount_usdt, card_number, confirm=True)
            if res.get("status") == "success":
                txt = "✅ <b>Транзакция отправлена в блокчейн Polygon!</b>\\n\\n"
                txt += f"• Сумма обмена: <b>${amount_usdt:.2f} USDT</b>\\n"
                txt += f"• Ожидается: <b>{res.get('expected_uah'):.2f} UAH</b>\\n"
                txt += f"• Карта: <code>{card_number[:4]} **** **** {card_number[-4:]}</code>\\n"
                txt += f"• TxHash: <code>{res.get('tx_hash')}</code>\\n\\n"
                txt += "Зачисление гривен произойдет автоматически в течение 5-10 минут."
                api.send_message(chat_id, txt)
                pending_file.unlink(missing_ok=True)
            else:
                api.send_message(chat_id, f"❌ Ошибка перевода: {res.get('error')}")
        except Exception as e:
            api.send_message(chat_id, f"❌ Критическая ошибка Web3: {e}")
        return True

    # 12. Сканирование рантайм-ошибок (SRE Healer)
    if any(phrase in t for phrase in ("сканируй ошибки", "сканировать ошибки", "sre healer", "найти баги")):
        api.send_message(chat_id, "🔎 <b>Запускаю сканирование системного лога на ошибки...</b>")
        from aios_core.sre_healer import SRESelfReflectiveHealer
        healer = SRESelfReflectiveHealer()
        try:
            tb_info = healer.scan_log_for_traceback(str(PROJECT_ROOT / "logs" / "telegram_bot.log"))
            if not tb_info:
                api.send_message(chat_id, "🟢 <b>SRE Healer:</b> В системных логах не обнаружено свежих трейсбеков. Код полностью здоров!")
            else:
                lines = [
                    "🚨 <b>SRE Healer зафиксировал рантайм-сбой в коде:</b>\n",
                    f"• Файл: <code>{tb_info['file_path']}</code>\n",
                    f"• Строка: <b>{tb_info['line_number']}</b>\n",
                    f"• Трейсбек:\n<pre>{tb_info['traceback'][:400]}</pre>\n",
                    "Для запуска ИИ-исправления и авто-патча кода напишите: <code>исправь ошибку</code>"
                ]
                api.send_message(chat_id, "".join(lines))
        except Exception as e:
            api.send_message(chat_id, f"❌ Ошибка сканирования логов: {e}")
        return True

    # 13. Автоматическое ИИ-исправление рантайм-ошибки
    if any(phrase in t for phrase in ("исправь ошибку", "исправить ошибку", "sre heal", "автопатч")):
        from aios_core.sre_healer import SRESelfReflectiveHealer
        healer = SRESelfReflectiveHealer()
        try:
            tb_info = healer.scan_log_for_traceback(str(PROJECT_ROOT / "logs" / "telegram_bot.log"))
            if not tb_info:
                api.send_message(chat_id, "❌ Нет активных сбоев для авто-исправления.")
                return True

            api.send_message(chat_id, f"🛠 <b>Запуск ИИ-исправления сбойного файла {Path(tb_info['file_path']).name}...</b>")
            res = healer.apply_ai_fix(tb_info)
            if res.get("status") == "success":
                txt = "✅ <b>ИИ-Автопатч успешно применен!</b>\\n\\n"
                txt += f"• Файл: <code>{res.get('file')}</code>\\n"
                txt += f"• Диагноз ИИ: <i>{res.get('diagnosis')}</i>\\n\\n"
                txt += f"• Изменение успешно скомпилировано и записано на диск."
                api.send_message(chat_id, txt)
            else:
                api.send_message(chat_id, f"❌ Не удалось исправить ошибку: {res.get('error')}")
        except Exception as e:
            api.send_message(chat_id, f"❌ Критическая ошибка ИИ-восстановления: {e}")
        return True

    return False
