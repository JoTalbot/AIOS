---
name: dr-config-preflight
description: Единый bounded preflight и schema/introspection слой для DR/bootstrap/snapshot/memory scripts.
---

# SKILL: dr-config-preflight
**Категория:** core
**Дата создания:** 2026-06-30

## Описание
Единый bounded preflight и schema/introspection слой для DR/bootstrap/snapshot/memory scripts.
Навык печатает effective non-secret config, schema по scope, readiness flags, warnings/errors
и пишет JSON/Markdown отчёты в `reports/`.

## Инструкции
1. Использовать перед изменениями, аудитом или рефакторингом DR/bootstrap путей.
2. Не печатать секреты; показывать только non-secret config и presence flags.
3. При ошибках не выполнять destructive действия, а формировать отчёт, причины и next step.
4. Для schema/introspection использовать `--schema`, для operational readiness — обычный preflight.

## Алгоритм
1. Загрузить env files через unified loader `/opt/octopus_dr_config.py`.
2. Для каждого scope собрать effective non-secret config и schema полей.
3. Выполнить bounded preflight checks: env files, paths, required values, fallback readiness, policy flags.
4. Сформировать JSON и Markdown отчёт в `reports/`.
5. Вернуть статус `ok`/`warnings`/`errors`, readiness flags и следующий bounded шаг.

## Команды
- `python3 /opt/octopus_dr_config.py --scope all --json`
- `python3 /opt/octopus_dr_config.py --scope snapshot --schema --json`
- `python3 /root/agents/-Octopus/scripts/dr_config_preflight.py --scope all --json`
- `python3 /root/agents/-Octopus/scripts/dr_config_preflight.py --scope bootstrap --schema --json`
- `python3 code/run.py --scope all --json`

## Контроль и развитие
- Runtime: `code/run.py --json`.
- Contract tests: `tests/test_contract.py`.
- Smoke tests: `tests/test_smoke.py`.
- Артефакты: `/opt/octopus_dr_config.py`, `scripts/dr_config_preflight.py`.
- Развитие: расширять checks и schema без раскрытия секретов и без влияния на активный control-plane.
