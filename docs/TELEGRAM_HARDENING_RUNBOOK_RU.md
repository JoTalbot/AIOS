# Telegram hardening: runtime, Colab mode и off-host DR

## FHS runtime

Production Telegram subsystem не пишет в Git checkout:

- state: `/var/lib/aios/telegram` (`0700`);
- logs: `/var/log/aios/telegram` (`0700`);
- queue backups: `/var/backups/aios/telegram-queues` (`0700`);
- local key escrow: `/var/backups/aios/telegram-queue-keys` (`0700`);
- root-only credential sources: `/etc/aios/credentials` (`0700`, files `0600`);
- ephemeral Docker credentials: `/run/aios-docker-credentials` (`0750`, files `0440`).

Controlled migration выполняется только при остановленных writers:

```bash
systemctl stop aios-telegram-bot.service \
  aios-telegram-metrics-snapshot.service
/opt/aios/.venv/bin/python scripts/migrate_telegram_runtime.py --remove-source
scripts/install_telegram_resilience_units.sh
systemctl start aios-telegram-bot.service
```

Migration checksum-проверяет каждый файл и не затрагивает unrelated audio или
другие файлы из `/root/AIOS/data`.

## Изоляция bot

Bot работает от `aios-telegram`, без root/sudo/capabilities. `/cmd` допускает
только read-only allowlist (`uptime`, `free -m`, `df -h`, короткие Git status/log
и `systemctl is-active` для ограниченного списка units). Shell, pipes,
redirections, чтение environment/credentials, restart и package operations
запрещены. Привилегированное администрирование выполняется только по SSH.

Неавторизованные Telegram chats silently dropped: bot не отвечает и не
раскрывает существование owner interface.

## Colab operating mode

Mode хранится в `/etc/aios/colab-mode`:

- `active` — canary требует `colab/qwen2.5-coder`;
- `maintenance` — Colab не вызывается, требуется managed free Qwen route;
- `human_action_required` — то же, плюс отдельный informational alert;
- `disabled` — Colab полностью исключён из routing.

При текущей CAPTCHA используется:

```text
LLMBalancer -> Groq -> qwen/qwen3.6-27b
```

Это бесплатный rate-limited managed inference fallback. Он не является SLA
заменой выделенному GPU. Автоматический обход CAPTCHA запрещён. Для возврата
Colab сначала владелец завершает CAPTCHA, затем меняет mode на `active` и
запускает managed keeper вручную.

## Immutable off-host backup — Backblaze B2

Выбран Backblaze B2: первые 10 GB доступны бесплатно, S3 API поддерживает Object
Lock. В аккаунте вручную создать private bucket с **Object Lock enabled at
creation** и restricted application key только для этого bucket.

Не передавать credentials в chat или shell arguments. Установить их через
root-only interactive input в:

- `/etc/aios/credentials/b2_access_key_id`;
- `/etc/aios/credentials/b2_secret_access_key`.

Non-secret настройки записываются в `/etc/aios/offsite-backup.env`:

```text
AIOS_B2_ENDPOINT=https://s3.<region>.backblazeb2.com
AIOS_B2_REGION=<region>
AIOS_B2_BUCKET=<private-bucket>
AIOS_B2_PREFIX=aios/telegram
```

`telegram_offsite_backup_key` генерируется installer автоматически. Владелец
должен забрать отдельную offline-копию этого ключа; без неё off-host bundle не
восстановить после полной потери VPS.

Uploader:

1. берёт последний WAL-safe backup и соответствующую queue key escrow copy;
2. создаёт tar bundle;
3. шифрует streaming AES-256-GCM отдельным ключом;
4. локально выполняет decrypt/hash round trip;
5. загружает через S3 API с 30-дневным Governance Object Lock;
6. проверяет remote size и SHA-256 metadata;
7. удаляет plaintext/temporary bundle.

До создания B2 account timer остаётся безопасно настроенным, но state/metrics
показывают `configured=0` и informational alert.

## Supply chain

- Все GitHub Actions закреплены полным 40-character commit SHA.
- Production images закреплены `version@sha256:digest`.
- CI отклоняет blobs больше 50 MiB и runtime credential/database sidecars.
- Release image проходит HIGH/CRITICAL Trivy gate.
- Для tag release создаётся CycloneDX SBOM.
- Immutable image digest подписывается keyless Cosign через GitHub OIDC.

## Queue fencing и incident policy

Generation и outbox lease имеют монотонный `lease_epoch`. Renew, finish и
failure transition выполняются compare-and-swap по worker ID и epoch. Старый
worker не может завершить или перезаписать reassigned job. Telegram ambiguous
send остаётся `failed_unknown`; automatic resend запрещён.

Регулярные fault tests покрывают stale worker, SIGTERM/drain, ambiguous timeout,
SQLite lock, simulated disk full, tampered encrypted bundle и delete failure.
