# AIOS 9.0.0-alpha.21 — релиз-ноты

> 2026-07-21 · **925 тестов зелёные** (было 906)
> Батч H2: масштабирование флота — наблюдаемость, web-pane и
> Facebook Marketplace; кодификация on-device калибровки (H1.5).

## Что нового

### 1. Calibrate-рецепт: on-device hints теперь процедура, а не магия

`platforms/recipe.py::calibration_recipe` строит точный сценарий
снятия ADB-дампов и калибровки под профиль платформы:

- **messenger-first** (WhatsApp/Viber): только инбокс-дамп;
- **collector** (TikTok): лента + tab-bar навигация;
- **marketplace** (OLX/Facebook/Instagram): cards + detail +
  messenger + navigation.

Уже закрытые секции пропускаются, serial устройства подставляется в
команды. Ничего не выполняется автоматически: рецепт — это план для
оператора, guarded-принцип соблюдён.

```bash
aios platforms doctor --platform whatsapp --calibrate-recipe
```

### 2. Ops-dashboard: read-only web-pane поверх REST-plane

`GET /dashboard` отдаёт самодостаточную HTML-панель (inline CSS/JS,
без CDN): очередь джобов со статусами, статистика pending/claimed/
done/failed + stale_claimed + heartbeats, пул устройств, профили,
shard-host. Панель только наблюдает — никаких действий из UI.

### 3. Facebook Marketplace — шестой онбординг-пакет в каталоге

OLX-like платформа полного стека: `platforms/facebook.yaml` +
`aios_core/modules/facebook/` (Storage/Messenger/Bootstrap),
CLI `aios facebook doctor|chats|dm-send|dm-flush|dm-outbox`.
Compliance-флаги: сбор read-only, ответы только через approval-
outbox, автопостинг запрещён (ToS Meta). Глубока-ссылка инбокса
`fb://messaging`.

### 4. Prometheus-метрики флота

`platforms/telemetry.py` + доработанный `/metrics`:

```
aios_shard_jobs{status="pending|claimed|done|failed"}
aios_shard_job_queue_depth, aios_shard_jobs_stale_claimed
aios_shard_hosts
aios_devices{state="registered|free|leased"}, aios_device_limits
aios_profiles_total, aios_profiles{platform="..."}
aios_catalog_platforms
```

`deploy/monitoring/` — готовый локальный стек: prometheus.yml,
Grafana-дашборд (`grafana-aios-ops.json`) с панелями очереди/пула/
профилей и README с командами запуска.

## Документация

- `docs/modules/{whatsapp,viber,tiktok,facebook}/ONBOARDING.md` —
  пошаговые on-device чек-листы под каждый пакет.
- `docs/ROADMAP_FULL.md` — H2.7/8/9 отмечены выполненными; H1.5
  кодифицирован рецептами (остаётся прогон на живом устройстве).

## Миграция

Никаких ломающих изменений: `/metrics` сменил формат с JSON-строки на
канонический Prometheus plain-text (endpoint ранее в HTTP-пути
фактически не работал — возвращал fallback-заглушку).

## Что дальше (roadmap)

- H1.5 ops-шаг: прогон calibrate-рецептов на живом Android-устройстве
  для всего флота, `marker-check` baseline.
- H2.10: compliance-принуждение на уровне resolver (rate-limits и
  no-autopost из флагов дескриптора) + audit-log.
- H2.9 продолжение: cards/cycle и drift-events счётчики, alert-правила.

## Напоминания по безопасности

1. Отзовите GitHub-токен, засвеченный в чате.
2. Смените пароль Instagram (тоже засвечен).
