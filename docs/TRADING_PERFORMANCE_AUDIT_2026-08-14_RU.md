# Аудит AIOS Trading — 2026-08-14

## Краткий вывод

Текущий модуль работает только в **paper trading** и не создаёт реальные биржевые ордера. Технически runtime стабилен, но статистического преимущества пока нет: все активные directional exchange-портфели имеют отрицательный realized PnL, а backtest/ML/RL не подтверждают готовность к live.

Рекомендация: не включать реальные деньги. Сначала заморозить новые paper-входы, исправить cost/accounting/timeframe, провести walk-forward и только после прохождения gates запускать новый paper-кандидат.

## Runtime

- `aios-quant-trading.service`: active, daemon, цикл 15 минут, без рестартов.
- `aios-market-data.service`: active, 1h candles каждые 15 минут, orderbooks.
- `aios-quant-ml-inference.service`: active, цикл 10 минут.
- Flash-arbitrage и liquidity-router активны отдельно.
- Текущий quant process после старта 2026-08-12 18:57 UTC: 69 циклов, 0 runtime errors.
- Три ошибки `MIN_CASH_RESERVE_PCT` относятся к предыдущему process и в текущем запуске не повторяются.

## Фактический paper-результат

### Multi-exchange

- Стартовый капитал: **$10,000.00**.
- Equity: **$9,924.43**.
- PnL: **−$75.57 (−0.756%)**.
- Realized PnL: около **−$65.99**.
- Unrealized PnL: около **−$9.59**.
- Cash: **$6,175.13**.
- Открытых позиций: **33**.
- Entry count: **225**; profitable closes: **74**.
- Приблизительно закрытых позиций: `entries - open = 192`; close win-rate около **38.5%**.
- Entry fees только в текущих открытых позициях: **$5.64**; closed fees отдельно не агрегируются.

### Дополнительные старые paper-контуры

Daemon параллельно ведёт ещё два независимых симулятора:

- Binance paper: около **−$11.81 (−1.18%)**, 2 открытые позиции.
- Kraken paper $100: около **−$1.69…−$1.76 (−1.7%)**, 5 открытых позиций.

Суммарно по трём независимым paper-контурам: примерно **−$89 на $11,100 (−0.80%)**. Эти балансы нельзя считать одним реальным счётом: стратегии частично дублируются.

## Динамика последнего snapshot

Сравнение `data/backup_stage/multi_exchange_portfolios.json` (около 04:54 UTC) и текущего состояния (около 11:25 UTC):

- realized PnL ухудшился ещё на **−$33.16**;
- новых entries: **28**;
- закрытий по изменению entries/open positions: примерно **30**;
- новых profitable closes: **2**;
- win-rate этого окна: примерно **6.7%**;
- средний realized результат закрытия: около **−$1.11**;
- открытых позиций стало на 2 меньше.

Это главный сигнал: текущая конфигурация продолжает быстро фиксировать отрицательную expectancy.

## Результаты по биржам

| Биржа | Realized PnL | Open | Approx. closed | Wins | Approx. close win-rate |
|---|---:|---:|---:|---:|---:|
| Kraken | −$19.96 | 5 | 43 | 15 | 34.9% |
| Binance | −$7.71 | 5 | 37 | 12 | 32.4% |
| Bybit | −$14.21 | 5 | 30 | 8 | 26.7% |
| OKX | −$9.75 | 5 | 28 | 10 | 35.7% |
| KuCoin | −$4.71 | 4 | 17 | 9 | 52.9% |
| Bitstamp | −$3.72 | 5 | 21 | 11 | 52.4% |
| MEXC | −$5.93 | 4 | 16 | 9 | 56.3% |

Даже кандидаты с более высоким win-rate пока имеют отрицательный realized PnL: одного процента wins недостаточно без среднего win/loss и costs.

## Arbitrage

- Settled arbitrage trades: **0**.
- Settled PnL: **$0**.
- Последняя theoretical opportunity: gross spread около 1.39%, theoretical PnL около $0.89.
- Theoretical opportunities правильно не включаются в equity.

До реализации depth/latency/inventory/withdrawal/gas/settlement такие сигналы нельзя считать доходом.

## Market data

- Основной повторяющийся дефект: **172 warnings** Coinbase orderbook `RNDR/USDC` (`no pricebook found`).
- Нужно заменить устаревший symbol mapping RNDR→RENDER либо исключить пару для Coinbase.
- Market-data собирает timeframe 1h каждые 15 минут; live engine тоже работает каждые 15 минут. Это может многократно использовать одну незакрытую часовую свечу и не совпадает с training/backtest timeframe.

## ML/RL и backtest

### Текущие сигналы

- ML signals: 33.
- `prob_up`: min 0.306, mean 0.427, max 0.526.
- При bullish threshold 0.65: **0 bullish**, 3 bearish.
- RL signals: 10; все position=0/flat, 0 long.

Модели не дают положительного long-edge; технические индикаторы продолжают открывать позиции без подтверждения ML/RL.

### Backtest summary, 32 актива

- Положительный ML return: 9/32.
- Средний ML return: **−2.26%**.
- Median: **−2.76%**.
- Sharpe >1: 5/32.
- Лучший: ADA +4.88%; худший: NEAR −7.51%.
- В summary нет прозрачного учёта fees/slippage/spread и walk-forward separation; результаты нельзя использовать как live gate.

## Почему стратегия убыточна

1. Round-trip fee моделируется как 0.30%, но directional execution использует last price без spread/slippage.
2. BUY разрешён по technical score без обязательного ML/RL edge.
3. До 5 позиций на каждой из 10 бирж; глобального portfolio drawdown kill-switch нет.
4. Коррелированные позиции по одним активам открываются на нескольких биржах.
5. SELL signal может закрывать до TP, фиксируя много небольших минусов/fees.
6. `total_trades` фактически считает entries, а UI win-rate делит wins на entries; accounting метрика вводит в заблуждение.
7. Одновременно работают legacy Binance/Kraken и multi-exchange симуляторы.
8. Timeframe live-сэмплов и backtest/model не согласован.

## Варианты развития

### A. Cost-aware directional v2 — рекомендуемый

1. Запретить новые entries при portfolio drawdown ниже −0.5%; существующие позиции только сопровождать/закрывать.
2. Использовать bid/ask и явный `fee + spread + slippage` на входе и выходе.
3. Вход только при ожидаемом edge минимум в 2–3 раза выше total cost.
4. Требовать согласие technical + ML; при ML max < threshold новых BUY нет.
5. RL flat использовать как veto, а не как слабый bearish point.
6. Ограничить 1–2 позиции глобально на correlated cluster, а не 5 на каждую биржу.
7. Добавить cooldown после loss и дневной loss limit.
8. Сначала оставить только shadow-кандидаты KuCoin/Bitstamp/MEXC; реальные деньги запрещены, пока PnL каждого не положителен после costs.

### B. Arbitrage-only paper

Отключить directional entries и развивать только market-neutral opportunities:

- учитывать orderbook depth, fees, slippage, transfer/gas, latency;
- моделировать inventory на обеих площадках;
- считать PnL только после simulated settlement;
- требовать net edge buffer и достаточный объём;
- не использовать flash-loan/live до минимум 100–200 settled paper trades.

### C. Monitoring/research only

Остановить исполнение paper-сделок, оставить market-data + ML/backtests. Использовать модуль как радар до появления подтверждённой стратегии. Самый безопасный режим.

### D. Ограниченный candidate portfolio

После исправления accounting/costs запустить новый чистый paper account:

- 1 timeframe (закрытая 1h свеча либо отдельно обученный 15m model);
- 3–5 ликвидных активов;
- 1–2 лучшие биржи;
- фиксированный risk 0.25–0.5% equity на позицию;
- no averaging down;
- автоматический kill-switch.

## Обязательные live-gates

До micro-live должны одновременно выполняться:

- не менее 200 закрытых paper trades и 30 дней;
- positive net expectancy после fees/spread/slippage;
- profit factor ≥1.20;
- Sharpe ≥1.0;
- max drawdown ≤3%;
- положительный результат walk-forward/out-of-sample;
- ни одной stale/illiquid/unpriced позиции;
- accounting: entries, closes, wins, gross PnL, fees, slippage, net PnL, MAE/MFE;
- ручное одобрение владельца.

Даже после gates прибыль не гарантируется. Начальный micro-live лимит должен быть минимальным и отделённым от основных средств.

## Выбранное направление

Владелец выбрал вариант **Cost-aware Directional v2**. Реализация и безопасный freeze-profile описаны в [`TRADING_DIRECTIONAL_V2.md`](TRADING_DIRECTIONAL_V2.md). Старые paper states сохраняются как исторический baseline; новый v2 account начинается отдельно.

Первый честный cost-aware walk-forward также отрицательный (OOS average −0.354%, PF 0.374), поэтому freeze подтверждён данными.

## Рекомендуемый порядок

1. Немедленно: freeze новых entries или остановка quant executor; market-data оставить.
2. Исправить RNDR/RENDER mapping и accounting метрики.
3. Реализовать costs + global kill-switch + timeframe alignment.
4. Пересчитать backtest с walk-forward и costs.
5. Запустить новый чистый paper candidate на 30 дней.
6. Решение о micro-live принимать только по gates.
