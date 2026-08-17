# Пакет Q1+Q2+Q3+Q6 — реализовано

**Дата:** 2026-08-15 | Ветка: agent/20260815-quant-oos-profit

## Q1 — Trade-flow коллектор (aggTrades)
- ws-коллектор расширен: подписка `{sym}usdt@aggTrade` на том же соединении;
- агрегация агрессорских объёмов за 5с → таблица `trades_ws` (buy_vol, sell_vol, buy_frac, n_trades);
- buy_frac (доля агрессорских покупок) — сильнейшая микроструктурная фича для сигнала;
- проверено: поток пишется по всем парам (XRP sell-heavy 640/5с, AVAX buy-heavy и т.д.).

## Q2 — `/quant` команда в TG-боте
- новый `tg_bot/quant_cmds.py` (НЕ protected): `cmd_quant()` — статус MM-сигналов с точностью,
  ws-данные, DCA, A/B, funding/OI, сервисы;
- `run_telegram_bot.py` (protected, правка владельцем одобрена): обёртка + ветка `/quant` + строка в `/help`;
- `selfguard --force-snapshot` выполнен (обязательно для protected-правки), бот перезапущен, активен;
- проверено: `/quant` выводит полный статус (MM 50% точность 3/6, ws 7.7k снапшотов, DCA, A/B).

## Q3 — Value-averaging для DCA (бэктест)
- `quant_dca_analysis.py`: добавлена VA-симуляция (вклад = план − факт, кап 2x/3x);
- результаты (12 мес): **VA top-10 + ребаланс (кап 2x): −17.21%** — лучший вариант
  (DCA+ребаланс −18.87%, DCA −32.66%, VA кап 3x −28.35% при maxDD −11.47%);
- вывод: VA с ребалансом чуть лучше DCA+ребаланс и заметно снижает просадку при кап 3x.
- Рекомендация: при переходе на реальные деньги рассмотреть VA top-10 + ребаланс.

## Q6 — ws-коллектор на 20 пар
- пары: BTC ETH SOL XRP BNB DOGE ADA TRX TON LINK AVAX UNI NEAR LTC DOT SUI APT ARB OP INJ;
- все 20 подключений активны (проверено журналом); данные 1Гц по 20 парам + trade-flow.

## Статус сервисов
- aios-orderbook-ws.service: active (20 пар, depth+aggTrade);
- aios-telegram-bot.service: active (после правки + selfguard);
- остальные таймеры (mm-monitor, mm-emitter, dca, dca-report, funding-oi): active.
