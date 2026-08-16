# Advisory claim: freqtrade T2 port validation + executor scaffold

- Агент: arena-agent (внешний, через SSH root@167.233.95.7)
- Дата: 2026-08-16
- Ветка: agent/20260815-quant-oos-profit

## Ожидаемые изменяемые пути (только они)
- scripts/freqtrade_t2.py (перезапись)
- scripts/freqtrade_config_t2.json (перезапись)
- scripts/freqtrade_validation/ (новый каталог: run_validation.py, reference_t2.py,
  download_binance.py, test_freqtrade_t2.py)
- scripts/run_t2_executor.py, scripts/config_executor.example.json, scripts/test_executor.py
- docs/FREQTRADE_VALIDATION.md
- coordination/sessions/20260816T030000Z-freqtrade-validation.md
- coordination/claims/20260816-freqtrade.md

## НЕ трогаю (чужая работа)
- catboost_info/*, tests/test_news_pipeline.py, backups/, любые файлы из
  git status, не перечисленные выше.

## Инфраструктурные изменения вне git (документированы)
- /root/freqtrade-venv (venv freqtrade 2026.7)
- /root/AIOS/data/freqtrade/ (user_data, данные, результаты бэктестов)
- Патч ccxt spot-only в /root/freqtrade-venv/lib/python3.11/site-packages/ccxt/
- /etc/systemd/system/aios-freqtrade-t2-dry.service (dry-run бот)
