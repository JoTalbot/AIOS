# AIOS Cost-aware Directional Trading v2

## Статус

Directional v2 работает только как **paper trading**. Реальные ордера не реализованы и запрещены до отдельного operator approval после прохождения всех gates.

Текущий безопасный режим:

```text
AIOS_QUANT_ENTRY_MODE=freeze
AIOS_QUANT_LEGACY_EXECUTION=0
AIOS_QUANT_PORTFOLIO_FILE=multi_exchange_portfolios_v2.json
```

`freeze` сопровождает/закрывает существующие v2 paper-позиции, но не открывает новые.

## Что исправлено

- Отдельный чистый v2 portfolio; legacy Binance/Kraken и старый multi state не смешиваются.
- Legacy duplicate execution выключен по умолчанию.
- Directional signals обрабатываются один раз на закрытую часовую candle.
- Round-trip cost model по умолчанию: taker fees 0.30% + half-spread/slippage 0.20% = около 0.50%.
- Entry требует confidence, ML confirmation и отсутствие RL veto.
- Global max positions: 2; per exchange: 1.
- Global drawdown и daily loss kill: 0.5% для новых entries.
- Любая unpriced позиция блокирует новые entries.
- Bearish signal закрывает только после min hold, confidence и bearish ML confirmation; TP/SL/trailing сохраняются.
- Accounting разделяет entries, closes, wins, gross PnL, fees, execution costs, net profit/loss и profit factor.
- Cross-exchange opportunities остаются theoretical, пока нет simulated settlement.
- Market symbols обновлены: `RENDER`, `POL` вместо устаревших `RNDR`, `MATIC`.

## Systemd profile

Ключевые ограничения заданы в `deploy/systemd/aios-quant-trading.service`:

| Переменная | Значение |
|---|---|
| `AIOS_QUANT_ENTRY_MODE` | `freeze` |
| `AIOS_QUANT_ALLOWED_EXCHANGES` | `kucoin,bitstamp,mexc` |
| `AIOS_QUANT_MAX_GLOBAL_POSITIONS` | `2` |
| `AIOS_QUANT_MAX_PER_EXCHANGE` | `1` |
| `AIOS_QUANT_MAX_DRAWDOWN_PCT` | `0.5` |
| `AIOS_QUANT_MAX_DAILY_LOSS_PCT` | `0.5` |
| `AIOS_QUANT_MIN_CONFIDENCE` | `0.82` |
| `AIOS_QUANT_ML_MIN_PROB` | `0.60` |
| `AIOS_QUANT_RL_VETO` | `0.30` |
| `AIOS_QUANT_MIN_HOLD_SECONDS` | `7200` |
| `AIOS_QUANT_CANDLE_SECONDS` | `3600` |

Allowed exchanges — только paper-кандидаты из аудита; это не утверждение об их прибыльности.

## Live-readiness gate

```bash
source /opt/aios/.venv/bin/activate
python scripts/check_quant_v2_gate.py
```

Gate требует одновременно:

- cost model `directional_v2`;
- walk-forward backtest;
- минимум 20 активов в backtest;
- положительный средний backtest return и ≥50% положительных активов;
- 30 дней нового paper account;
- минимум 200 закрытых сделок;
- positive net realized PnL;
- profit factor ≥1.20;
- max drawdown ≤3%;
- 0 unpriced positions.

Любой failed check означает: `entry_mode` нельзя переводить в `enabled`, live запрещён.

## Проверка

```bash
pytest -q \
  tests/test_quant_directional_policy.py \
  tests/test_quant_directional_v2.py \
  tests/test_quant_v2_gate.py \
  tests/test_quant_trading_accounting.py \
  tests/test_quant_trading_fees_risk.py \
  tests/test_run_quant_trading_v2.py

systemd-analyze verify deploy/systemd/aios-quant-trading.service
```

## Rollout freeze-mode

1. Создать backup старых paper JSON.
2. Установить versioned unit в `/etc/systemd/system/`.
3. `systemctl daemon-reload`.
4. Запустить service.
5. Убедиться, что создан `multi_exchange_portfolios_v2.json`.
6. Проверить: entry mode freeze, 0 entries/open positions, risk state заполнен.
7. Проверить market-data warning RNDR/USDC после обновления collector.

## Walk-forward status

Offline generator: `scripts/run_quant_walkforward_v2.py`. Artifact: `data/reports/backtest_directional_v2.json`.

Первый cost-aware OOS run на 35 активах не прошёл gates: average −0.354%, positive 34.3%, PF 0.374. Подробности: [`TRADING_WALK_FORWARD_2026-08-14_RU.md`](TRADING_WALK_FORWARD_2026-08-14_RU.md). Entry mode остаётся `freeze`.

Следующая версия стратегии должна получить новый untouched OOS window; подбирать параметры на текущем test-сегменте запрещено.

Положительный результат не гарантирован даже после gates. Любой micro-live — отдельное решение владельца, минимальный изолированный капитал и ручное подтверждение.
