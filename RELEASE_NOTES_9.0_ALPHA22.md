# AIOS 9.0.0 — релиз-ноты

> 2026-07-21 · **939 тестов зелёные** (было 925)
> Батч H2.10 + добивка H2.9: compliance-принуждение, audit-log,
> счётчики телеметрии и alert-правила.

## Compliance-контур: guarded теперь и правовой

`aios_core/platforms/compliance.py` переводит ToS-флаги дескриптора
(`extras.compliance`) в проверки на границах действий:

| Действие | Разрешено, если |
| --- | --- |
| `autopost` (публикация, даже с confirm) | `autopost_allowed: true` |
| `collect` (сбор ленты read-only) | `collector: true` |
| `send` (черновик в outbox) | `messenger != none` |
| `auto_send` (прямая запись на устройство) | `messenger: open` |

- Проверка происходит **до** инициализации устройства: CLI dm-send,
  generic reels, Instagram PostComposer честно отвечают
  `{"error": ..., "compliance": {...}}`, ничего не трогая железо.
- Платформа без блока compliance = «политика не задекларирована» →
  deny-by-default (scaffold выдаёт такой блок сразу).
- В дескрипторы OLX/Instagram добавлены compliance-секции:
  сбор read-only, ответы строго через approval-outbox, постинг
  только с явным `--confirm`; `actions_per_hour` для pacing.

## Audit-log: каждое guarded-действие оставляет след

Таблица `olx_audit` (миграцирует через CREATE IF NOT EXISTS) +
`audit()/audit_list()`. Outbox-жизненный цикл (постановка черновика,
переходы статусов) пишется автоматически в OLXStorage — наследуют
все платформы (WA/Viber/TikTok/Facebook/Instagram).

## Наблюдаемость: счётчики и alert-правила

- `aios_seen_receipts{platform,kind}` — объёмы показов ad/video из
  per-platform БД `data/*.sqlite`;
- `aios_outbox_pending{platform}` — очередь одобрения;
- `deploy/monitoring/aios-alerts.yml` — 7 правил: падение агента,
  отсутствие живых worker'ов при pending-джобах, бэклог >50/>200,
  зависшие claim'ы, исчерпание пула устройств, отставание одобрений
  outbox >100 за час. Уже подключено в prometheus.yml.

## Миграция

Существующие БД автоматически получают таблицу `olx_audit`. Если у
вашей самописной платформы нет `extras.compliance` в дескрипторе —
guarded-действия будут честно отклонены: добавьте блок (шаблон в
`aios platforms scaffold`).

## Что дальше

- H1.5: прогон calibrate-рецептов на живом Android-устройстве всего
  флота + `marker-check` baseline.
- H2.13: K8s operator (CRD Platform/Profile/Job).
- H3.11: AI-советник Direct-ответов (draft-only в outbox).

## Напоминания по безопасности

1. Отзовите GitHub-токен, засвеченный в чате.
2. Смените пароль Instagram (тоже засвечен).
