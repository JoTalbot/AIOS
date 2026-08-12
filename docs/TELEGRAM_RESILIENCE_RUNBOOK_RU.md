# Telegram resilience: backup, restore и ротация секретов

## Очереди

`aios-telegram-queue-backup.timer` ежедневно вызывает SQLite Online Backup API.
WAL-файлы копировать вручную не требуется. Базы сохраняются в
`/root/AIOS/backups/telegram-queues/<UTC timestamp>/`, а соответствующая Fernet
key-копия — отдельно в `/root/aios-secret-backups/telegram-queue-keys/`.
Оба каталога имеют mode `0700`, файлы — `0600`.

Еженедельный `aios-telegram-queue-restore-drill.timer` проверяет SHA-256,
`PRAGMA integrity_check` и пробное расшифрование payload. Значения payload и
ключей не выводятся.

Ручная проверка последней копии:

```bash
/opt/aios/.venv/bin/python scripts/telegram_queue_backup.py --verify-latest
```

Восстановление всегда выполняется сначала в новый каталог:

```bash
/opt/aios/.venv/bin/python scripts/telegram_queue_backup.py \
  --verify /root/AIOS/backups/telegram-queues/<timestamp> \
  --restore-to /root/telegram-restore-drill/<timestamp>
```

Для production restore остановить bot, сделать incident backup текущих файлов,
проверить отсутствие активных `sending/generating`, заменить базы только из
проверенного restore-каталога и лишь затем запустить bot. `failed_unknown`
никогда не переводить в automatic retry.

## Секреты

Canonical source: `/etc/aios/credentials/`, directory `0700`, files `0600`.
`install_telegram_resilience_units.sh` переносит managed secrets и удаляет
`AIOS_TELEGRAM_TOKEN`, `TELEGRAM_BOT_TOKEN`, `COLAB_LLM_API_KEY`,
`TAILSCALE_AUTH_KEY` и owner chat ID из legacy env-файлов. Проверка без вывода значений:

```bash
python scripts/audit_legacy_secrets.py --fail-on-findings
```

Colab Bearer key автоматически меняется при полном recovery. Telegram bot token
нельзя создать или отозвать через Bot API: новый token выдаётся владельцем через
BotFather. Для его ротации записать новый token во временный root-only файл,
атомарно заменить `/etc/aios/credentials/telegram_token`, выполнить controlled
restart зависимых units, запустить оба full canary и только после успеха удалить
временный файл, удалить rollback-копию старого credential и отозвать старый
token.

Не передавать token в аргументах процесса, shell history, Git, alert annotations
или backup manifest.
