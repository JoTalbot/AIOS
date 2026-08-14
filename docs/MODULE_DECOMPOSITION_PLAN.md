# План безопасной декомпозиции крупных модулей

## Правило

Никаких массовых rewrite. Один PR/commit извлекает один связный seam, сохраняет старые import paths через re-export/delegation и добавляет regression tests до удаления исходного тела.

Размеры и spans блокируются `scripts/check_module_size_budget.py --strict`.

## Выполнено

### Quant report formatters

Из `aios_core/quant_trading_engine.py` вынесены шесть pure presentation functions в `aios_core/quant_report_formatters.py`:

- `format_kraken_demo_report`;
- `format_unified_crypto_earnings_report`;
- `format_positions_only_report`;
- `format_single_asset_analysis`;
- `format_backtest_report`;
- `format_portfolio_advice_report`.

Старый модуль re-export сохраняет публичный API. Trading/state/network logic не изменена. Монолит уменьшен с 2 156 до 1 898 строк.

`format_multi_exchange_demo_report` пока остаётся: он создаёт sentiment/DeFi helpers и требует отдельного dependency-injection seam.

## Следующие seams

### `tg_bot/accounts.py`

Текущая проблема: `_handle_account_intent` занимает около 2 875 строк и использует module globals.

Порядок:

1. Ввести небольшой `AccountIntentContext` с API, chat ID, project root и adapters.
2. Вынести analytics/post scheduling как первый handler с контрактом `handled: bool`.
3. Затем OLX price/autoreply/inventory handlers.
4. Оставить `_handle_account_intent` как ordered router; не менять приоритет intent matching за один раз.
5. На каждый handler — table-driven tests, запрещающие live network/data.

### `run_account_control.py`

1. Вынести Gmail IMAP pure parsing/read/send в `account_control/google_mail.py`.
2. Вынести Google browser Calendar/Drive/Docs в отдельный adapter.
3. Вынести Instagram DM/profile, затем desktop messenger wrappers.
4. `main()` оставить CLI router с прежними subcommands/output JSON.

### `aios_core/dashboard.py`

1. Не разбивать stateful `AIOSDashboard` механически.
2. Сначала вынести pure card/table rendering и query helpers.
3. Затем page builders по областям: ops, LLM, finance, phone.
4. Сохранить lazy imports и существующий `create_dashboard()` API.

## Бюджеты

Текущие line budgets — верхняя граница, а не целевой размер:

- `aios_core/dashboard.py`: 3 494;
- `tg_bot/accounts.py`: 3 225;
- `run_account_control.py`: 2 374;
- `aios_core/quant_trading_engine.py`: 1 900;
- `aios_core/quant_report_formatters.py`: 320.

Новая функциональность не добавляется внутрь монолита, если её можно направить в submodule. Budget повышается только отдельным architecture review с объяснением.

## Проверка

```bash
python scripts/check_module_size_budget.py --strict
pytest tests/test_module_size_budget.py tests/test_quant_report_formatters.py -q
python scripts/generate_project_inventory.py --write
```
