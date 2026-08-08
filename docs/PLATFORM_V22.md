# AIOS Platform v22 — Groundwork Spec

Статус: **Phase A (groundwork) реализована** 2026-08-08. Phase B (пилот) — за решением владельца.

## Продукт

AIOS наружу как платный API для внешних клиентов. Первый клиентский сегмент — **автоназборки и реселлеры автозапчастей** (проверенная ниша: собственный склад + OLX-пайплайн уже в бою).

### Платные endpoint'ы (v22 groundwork, реализовано)

| Endpoint | Цена | Что делает | Источник данных |
|---|---|---|---|
| `GET /api/v2/mon/olx-price?query=` | $0.10 | Price intelligence: min/avg/median/max цены + сэмплы объявлений по запросу | `olx_http.sqlite` (1780+ живых объявлений, коллектор каждый час, 402 прогона) |
| `POST /api/v2/mon/code-audit` | $0.10 | ИИ-аудит безопасности/PEP8 Python-кода | LLM balancer |
| `POST /api/v2/mon/summarize` | $0.05 | Суммаризация текстов, извлечение тезисов | LLM balancer |
| `GET /api/v2/mon/products` | free | Каталог продуктов и тарифов | — |
| `GET /api/v2/mon/balance` | free | Баланс/счётчики по ключу | key store |

Auth: заголовок `X-API-Key` (коммерческий ключ `aios_live_*`, не путать с внутренними `AIOS_API_KEYS` middleware — при `AIOS_API_AUTH_REQUIRED=1` возможный конфликт middleware; в pilot-режиме container auth выключен).

### OLX Price Intelligence — главный датапродукт

- База: 12 запросов ниши (ваз/газель/шкода/bmw фары/разборки), 1784 объявления, растёт ежечасно
- Ценность для автоназборки: мгновенная рыночная вилка цены на деталь → быстрое ценообразование при приёме разборки
- Конкуренты: ручной мониторинг OLX (часы в день) — мы продаём $0.10/запрос или подписку

## Архитектура

```
клиент → X-API-Key → aios-api:8000 (Starlette)
  /api/v2/mon/* → APIMonetizationManager (verify_and_charge, 25/25/25/25 по кошелькам)
  olx-price → /app/hostdata/olx_http.sqlite (ro-mount хостовых данных коллектора)
  audit/summarize → LLMBalancer (groq/gemini fallback)
```

Файлы: `aios_core/api/monetization_routes.py` (routes+intel), `aios_core/api/app.py` (регистрация, `AIOS_MONETIZATION_ENABLED=0` выключает), `aios_core/api_monetization.py` (менеджер ключей), `docker-compose.prod.yml` (ro-монт `olx_http.sqlite`).

## Известные ограничения groundwork (к доработке в Phase B)

1. **Key store — JSON file** (`api_keys_monetization.json`): load+save на запрос, race при параллельности. Пилот-скейл ок (<10 rps), затем → sqlite/aios.sqlite.
2. **Порт 127.0.0.1:8000** — для внешних клиентов нужен reverse proxy (nginx/caddy) + `AIOS_API_AUTH_REQUIRED=0` конфликт middleware решить allowlist'ом `/api/v2/mon/*`.
3. ~~Rate limiting~~ ✅ v22-B: token bucket per-key, 30 req/мин (env `AIOS_MON_RATE_LIMIT_RPM`), 429 при превышении.
4. ~~Analytics~~ ✅ v22-B: JSONL ledger `api_usage_ledger.jsonl` на каждое списание (клиент/продукт/сумма) + `scripts/api_usage_report.py` — TG-дайджест выручки, cron 21:05.
5. **Выдача ключей** ручная (оператор после депозита) — Phase B: webhook USDT→ключ автоматом.

## Phase B (пилот) — чеклист за approve владельца

- [ ] Открыть публичный доступ (proxy + TLS) к `/api/v2/mon/*`
- [ ] 1–2 пилотных клиента-автоназборки, выдать ключи, собрать обратную связь
- [ ] White-label: генерация объявлений клиенту в его стиле/аккаунте OLX (tenant-конфиг через `multitenancy.py`)
- [ ] Мониторинг выручки: funnel-отчёт API в ежедневный TG-дайджест

## Тесты

`tests/test_v22_api.py`: 3 теста (менеджер баланса/списаний, intel против sqlite-фикстуры, регистрация роутов). Зелёные 3/3.
