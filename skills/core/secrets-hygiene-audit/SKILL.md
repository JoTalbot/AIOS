---
name: secrets-hygiene-audit
description: Аудит гигиены секретов: bounded read-only поиск plaintext-кредов в инструкциях, конфигах, логах и коде. Реализует инструкцию №51 (Secrets Hygiene).
---

# SKILL: secrets-hygiene-audit
**Категория:** core / security
**Дата создания:** 2026-06-20
**Реализовано:** 2026-07-13 (заменён generic runtime на реальную логику)

## Описание
Аудит гигиены секретов: bounded read-only поиск plaintext-кредов в инструкциях, конфигах, логах и коде. Реализует инструкцию №51 (Secrets Hygiene).

## Алгоритм
1. Обход scan-roots (`/mnt/agents`, `/etc/octopus`) с лимитами: `MAX_FILES`, `MAX_FILE_BYTES` (512 KB), пропуск бинарных файлов (null-byte в первых 1024 байт).
2. Пропуск designated-хранилищ (allowlist): `/etc/octopus/secrets.env`, `~/.gh_token`, `~/.railway_token`, файлы `*.token`/`*.pem`/`*.key` — это КОРРЕКТНЫЕ места для секретов.
3. Пропуск шумовых/сгенерированных директорий: `.git`, `__pycache__`, `_reorg_backups`, `_backup`, `_archived_dupes`, `_en`, `node_modules`, `.venv`.
4. Поиск по сигнатурам (паттернам):
   - `private_key_block` (`-----BEGIN ... PRIVATE KEY-----`) — **critical**;
   - `github_token` (`ghp_/gho_/ghs_…` 36 символов), `aws_access_key_id` (`AKIA…`), `aws_secret_access_key`, `google_api_key` (`AIza…`), `slack_token` (`xox…`) — **high**;
   - `bearer_token_long` (`Bearer <40+ alnum>`), `generic_long_hex_token` (64-hex) — **medium**.
5. Фильтрация плейсхолдеров: `<REDACTED>`, `${ENV}`, `xxx`, короткие значения, слова без энтропии — НЕ считаются утечкой (избегаем ложных срабатываний на документации).
6. **Маскирование:** каждое совпадение выводится как `первые3 + *** + последний` символ. Контекст-строка тоже маскируется. Полное значение секрета НИКОГДА не попадает в отчёт (`secret_values_emitted: false`).
7. Дедупликация (тип + файл + masked), сводка по severity, allowlist-проверка наличия designated-хранилищ.
8. Read-only: файлы только читаются, ничего не изменяется/удаляется. exit=1 если есть critical/high.

## Контракт безопасности
- `read_only: true` — никогда не пишет/не удаляет.
- `secret_values_emitted: false` — значения маскируются.
- bounded — лимиты файлов/размера, таймаутов нет (синхронный read).

## Runtime
```bash
python3 code/run.py --json
python3 code/run.py --root /custom/path --json
```

## Контроль и развитие
- Contract tests: `tests/test_contract.py` (детекция, маскирование, плейсхолдеры, allowlist, интеграция).
- Расширение паттернов: добавлять новые сигнатуры в `PATTERNS` (id, regex, severity).
- Связь: инструкция №51 (гигиена секретов), №12/№44 (известные plaintext-креды — кандидаты на ротацию).
