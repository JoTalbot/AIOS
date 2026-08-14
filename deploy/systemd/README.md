# AIOS systemd desired state

Этот каталог хранит воспроизводимое описание systemd для текущего production-хоста без автоматического применения.

## Слои

1. `deploy/systemd/*.service|*.timer` — canonical unit definitions.
2. `deploy/systemd/<unit>.d/*.conf` — tracked drop-ins.
3. `deploy/systemd/host-overrides/hetzner/` — exact base-unit variants текущего Hetzner-хоста, когда они намеренно отличаются от canonical.
4. `HETZNER_MASKED_UNITS.txt` — units, представленные на хосте mask symlink `/dev/null`.
5. `HETZNER_INSTALLED_UNITS.txt` — read-only name snapshot установленного `aios-*` профиля.

Наличие файла в Git не означает, что агент может выполнить `systemctl enable/restart`. Применение — отдельная operator-approved сессия с diff, `systemd-analyze verify`, backup, rollout и rollback.

## Профили

На Docker production host следующие tracked host-native units могут отсутствовать намеренно:

- `aios-api.service`;
- `aios-dash.service`;
- `aios-mcp.service`;
- `aios-tg.service`;
- `aios-tunnel.service`.

Они считаются optional-not-installed, а не drift.

## Host overrides

Host override не заменяет canonical definition. Он объясняет фактический base unit конкретного хоста. Перед удалением override нужно либо применить canonical unit на хосте, либо явно принять runtime variant как новый canonical.

Текущие overrides:

- `aios-colab-keeper.service` — inactive/disabled host variant;
- `aios-olx-collector.service` — active host query profile.

## Проверка

```bash
python scripts/audit_deployment_sources.py --runtime --strict --fail-on-runtime-drift
pytest tests/test_systemd_inventory.py -q
```

Strict audit сравнивает installed names, base-unit hashes, drop-ins и optional profile. Он ничего не изменяет.

## Безопасность

- `.bak` из `/etc/systemd/system` не импортируются.
- Embedded secrets запрещены; использовать `EnvironmentFile=`, systemd credentials или `/etc/aios/credentials`.
- Перед импортом/изменением обязателен redacted Gitleaks scan.
- Массовые restart/disable/remove запрещены.
