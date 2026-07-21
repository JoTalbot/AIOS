# AIOS 9.0.0-alpha.9 — Waitlist, ShardRouter, APK auto-scaffold

**Дата:** 2026-07-21 · **Тесты:** 725/725 зелёные · Python ≥ 3.10

Десятый выпуск закрывает очереди аренды устройств, шардинг профилей
по хостам и автогенерацию платформы из APK.

## Главное

### Waitlist аренды (очередь ожидания устройства)
- Идемпотентная очередь `pool_waitlist` с приоритетами
  (priority DESC → FIFO).
- Обслуживание **автоматическое**: `release()` и `reap_stale()` сразу
  выдают освободившиеся устройства ожидающим, соблюдая квоты
  `max_busy:<platform>`.
- CLI: `aios devices lease --enqueue --priority N | enqueue | waitlist |
  cancel-wait`.
- REST: lease с `{"enqueue": true}` → `202 Accepted {"queued": id}`,
  `GET /api/v1/devices/waitlist`, `POST .../waitlist/cancel`.

### ShardRouter — шардинг по хостам
- Профили адресуются `host/platform/name`; маршрут — rendezvous
  (HRW: max sha256(host|profile_key)), **липкий и персистентный**
  (`AIOS_SHARDS_DB`): один профиль всегда ведёт на один хост — важно
  для sticky-сессий устройств и хранилищ.
- Болезнь/удаление хоста → автоматическая перемаршрутизация.
- CLI: `aios shards add|list|remove|route|unroute`;
  REST: `/api/v1/shards` CRUD + `/api/v1/shards/route`.

### Авто-scaffold из APK
- `inspect_apk()` читает `aapt dump badging` → пакет, метка приложения,
  launchable-activity, target SDK.
- `scaffold_from_apk()` — черновой дескриптор и скелет платформы из APK
  одной командой: `aios platforms from-apk olx.apk [--name slando]
  [--dry-run]`.

## Цифры
- 725 автотестов (+13), ~66 REST-роутов, 46+ CLI-команд.
- Эксплуатационный контур завершён: scaffold → каталог → профили →
  квоты → пул+очередь → шардинг → cron.

## Установка
```bash
pip install dist/aios-9.0.0a9-py3-none-any.whl
```
