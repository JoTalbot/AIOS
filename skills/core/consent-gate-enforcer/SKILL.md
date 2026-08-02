---
name: consent-gate-enforcer
description: Bounded read-only аудитор consent-гейтов. Реализует инструкцию №18 (суверенитет человека): делает состояние всех consent-гейтов видимым и обнаруживает drift — систему, делающую то, что её гейты запрещают.
---

# SKILL: consent-gate-enforcer
**Категория:** core / security / governance
**Дата создания:** 2026-06-20
**Реализовано:** 2026-07-13 (заменён generic runtime на реальную логику)

## Описание
Bounded read-only аудитор consent-гейтов. Реализует инструкцию №18 (суверенитет человека): делает состояние всех consent-гейтов видимым и обнаруживает drift — систему, делающую то, что её гейты запрещают.

## Алгоритм
1. **Парсинг `human_consent.env`** (`/etc/octopus/human_consent.env`): чтение флагов `ALLOW_AUTONOMOUS_BASH`, `ALLOW_DEV_LOOPS`, `ALLOW_CLOUD_PROVISION`, интерпретация как open/closed/default_closed. Чтение `QUIET_HOURS_*`.
2. **Парсинг `consent.json`** (money-earner gate, #46): оценка interlock-цепочки — реальные ордера возможны ТОЛЬКО при `real_funds_unlocked AND execution_armed AND api_keys_present AND approved_exchanges≠[]`. Детекция drift: armed без keys, armed без exchanges, live без max_loss.
3. **Чтение `autonomy_state.json`** (`/run/octopus/`): статус автономного агента, last_action, health.
4. **Проверка systemd-units** (live, bounded): активен ли `octopus-autonomous-agent.timer`, присутствует ли `octopus-dev-loop.timer`.
5. **Drift detection** (cross-source, ключевая ценность):
   - CRITICAL: автономный агент активен, но `ALLOW_AUTONOMOUS_BASH=closed` → нарушение #18.
   - HIGH: финансовые misconfigurations (armed без keys/exchanges, live без kill-switch).
6. Формирование JSON-отчёта: dashboard гейтов + финансовый interlock + drifts + рекомендации. Read-only: ничего не меняет.

## Контракт безопасности
- `read_only: true` — никогда не открывает/закрывает гейты, не останавливает процессы.
- Emits consent dashboard для аудита, не для действия.

## Runtime
```bash
python3 code/run.py --json
python3 code/run.py --no-live --json   # без live systemd-проверок
```

## Контроль и развитие
- Contract tests: `tests/test_contract.py` (18 тестов: env-парсинг, gate-state, financial interlock, drift detection, интеграция).
- Связь: инструкция №18 (суверенитет), №46 (money gate), №13 (no autoloops).
