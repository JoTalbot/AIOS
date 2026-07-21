# AIOS 9.0.0-alpha.8 — Generic Module REST, квоты пула, cron-plan

**Дата:** 2026-07-21 · **Тесты:** 712/712 зелёные · Python ≥ 3.10

Девятый выпуск завершает связку мультиплатформенной архитектуры:
любая платформа из каталога автоматически получает REST data-plane,
пул устройств управляется квотами, а расписания генерируются командой.

## Главное

### Generic module surfaces (REST из дескриптора, ноль кода)
Каждая зарегистрированная платформа получает:
- `GET /api/v1/modules/{platform}/ads?query=&limit=&profile=`
- `POST /api/v1/modules/{platform}/ads/ingest` — вход для внешних
  коллекторов (AdCard JSON, идемпотентно)
- `GET .../stats` (анализ рынка по общей схеме)
- `GET .../ads/{fingerprint}/history` (история цен)
- `GET .../own` + `POST .../own/snapshot` (свои объявления)

`?profile=` работает как у OLX, хранилища кэшируются по
`platform:profile`. Статические роуты OLX матчатся первыми — поведение
OLX не изменилось; неизвестная платформа → 404. Связка со scaffold:
`scaffold → load_catalog → платформа на воздухе`.

### Квоты DevicePool
- `max_devices` — потолок регистраций;
- `max_busy:<platform>` — одновременных аренд на платформу (продление
  своей аренды и pinned-lease занятого другим — под контролем квоты);
- `max_avds` — защитный потолок auto-создаваемых AVD в `ensure_device`
  (по умолчанию 8).
- CLI: `aios devices limits [--set max_busy:olx=4]`;
  REST: `GET|POST /api/v1/devices/limits` (register сверх квоты → 400).

### `aios cron-plan`
Генерирует crontab из текущего реестра профилей:
```cron
*/15 * * * * cd /srv/AIOS && python3 aios_cli.py olx autowatch --profile work --webhook ... >> .../autowatch-olx_work.log 2>&1
*/15 * * * * cd /srv/AIOS && python3 aios_cli.py devices monitor --once >> .../pool-monitor.log 2>&1
```
`--platform`, `--interval`, `--webhook`, `--write /etc/cron.d/aios`.

## Цифры
- 712 автотестов (+7), ~54 REST-роута, 40+ CLI-команд.
- Полный цикл: scaffold → каталог → профили → квоты → устройства →
  cron-расписания.

## Установка
```bash
pip install dist/aios-9.0.0a8-py3-none-any.whl
```
