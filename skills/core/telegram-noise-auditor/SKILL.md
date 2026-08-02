---
name: telegram-noise-auditor
description: Bounded read-only аудитор политики Telegram-шума. Реализует инструкции №28 (единственный push-отправитель — автономный агент) и №32 (постоянная защита от возврата TG-шума). Классифицирует каждый Telegram-related systemd-
---

# SKILL: telegram-noise-auditor
**Категория:** core / telegram / governance
**Дата создания:** 2026-06-20
**Реализовано:** 2026-07-13 (заменён generic runtime на реальную логику)

## Описание
Bounded read-only аудитор политики Telegram-шума. Реализует инструкции №28 (единственный push-отправитель — автономный агент) и №32 (постоянная защита от возврата TG-шума). Классифицирует каждый Telegram-related systemd-unit по scope проекта и политике, флагает любой запрещённый Octopus-pusher как CRITICAL drift.

## Алгоритм
1. **Перечисление** всех systemd-units, имена которых начинаются с `octopus-`/`traff-`/`autohelp-` И содержат telegram/tg/notif/alert/watchdog.
2. **Классификация** каждого (pure function `classify_unit`):
   - **approved** — `octopus-tg-bot` (интерактивный бот, не push — №29);
   - **infra** — `octopus-telegram-drift-guard` (read-only guard, не pusher — №32);
   - **disallowed_pusher** — `octopus-alerting/alerts-tg/tg-notifier/watchdog` (запрещены, №28 sec.5);
   - **unknown_octopus_tg** — новый Octopus TG-unit вне таблиц (HIGH, №28: «не допускать новых отправителей»);
   - **other_project** — `traff-*`/`autohelp-*` (другой проект, НЕ подпадают под Octopus №28/№32);
   - **unrelated** — не TG.
3. **Drift detection**:
   - CRITICAL: disallowed_pusher активен/enabled → нарушение №28;
   - HIGH: unknown_octopus_tg активен → возможный новый отправитель.
4. **Чтение drift-guard отчёта** (`telegram_drift_guard_latest.json`, №32), если есть — сводка critical/warning.
5. JSON-отчёт: сводка по policy, активные approved-отправители, units, drifts, рекомендации. Read-only: ничего не останавливает, сам НЕ отправляет Telegram.

## Контракт безопасности
- `read_only: true`, `never_sends_telegram: true`.
- Project-scoped: корректно отличает Octopus-policy от других проектов на том же хосте.

## Runtime
```bash
python3 code/run.py --json
python3 code/run.py --no-live --json   # без live systemd-перечисления
```

## Контроль и развитие
- Contract tests: `tests/test_contract.py` (классификация, drift detection, потребление drift-guard отчёта, интеграция).
- Связь: №28 (clean reports), №32 (drift guard), №29 (bot panel).
