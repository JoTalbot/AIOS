# AIOS 9.0.0-alpha.5 — Platforms & Profiles: мультиакаунтность и архитектура для 10000+ приложений

**Дата:** 2026-07-21 · **Тесты:** 684/684 зелёные · Python ≥ 3.10

Шестой выпуск линейки OLX Agent переводит проект на архитектуру
«платформа → профили»: сколько угодно маркетплейс-приложений, в каждом —
сколько угодно аккаунтов, каждый со своим устройством и своими данными.

## Главное

### Реестр платформ (`aios_core/platforms`)
- `PlatformDescriptor`: Android-пакет, агентский модуль, фабрики
  хранилища и ADB. Реестр расширяется через `register_platform()` без
  правок существующего кода (Open/Closed) — OLX оформлен как эталон.
- `docs/PLATFORMS_SCALING.md` — дорожная карта к 10000+ приложений:
  каталог дескрипторов, кодогенерация CLI/REST из дескриптора, пул
  эмуляторов, шардинг по хостам.

### Профили (аккаунты)
- `Profile` = `platform:name` + `device_serial` + изолированное
  хранилище `data/<platform>/<profile>.sqlite` + локаль.
- Данные аккаунтов не смешиваются никогда — изоляция на уровне файлов.
- Реестр `ProfileStore` (SQLite, `AIOS_PROFILES_DB`) — CRUD и дефолты.
- Разрешение контекста едино для CLI и API:
  `--profile`/`?profile=` → `AIOS_PROFILE` → default реестра →
  эфемерный legacy-`default` (прежнее поведение сохранено полностью).

### Привязка к устройствам
- `ADBController(serial=...)`: все команды `adb -s <serial> …` —
  эмуляторы разных аккаунтов работают параллельно.
- Добавлены `tap()` и `input_text()` (ввод через ADBKeyBoard).

## Интерфейсы

**CLI**
```bash
aios platforms
aios profiles add --platform olx --name work --device emulator-5556 --default
aios profiles list|show|remove|set-default
aios olx stats --profile work        # все olx-команды принимают --profile
aios olx stats --db file.sqlite      # явный --db обходит реестр
```

**REST**
- `GET /api/v1/platforms`, `GET|POST /api/v1/profiles`,
  `GET|DELETE /api/v1/profiles/{platform}/{name}`,
  `POST /api/v1/profiles/{platform}/default`
- любой OLX-маршрут с `?profile=work` — хранилище переключается
  (кэшируется в процессе), неизвестный профиль → HTTP 400.

Философия guarded-action сохранена: профили меняют только то, *от чьего
имени* и *на каком устройстве* выполняются уже существующие guarded-операции.

## Цифры
- 684 автотеста (+17), 40+ REST-роутов, 27+ CLI-команд.

## Установка
```bash
pip install dist/aios-9.0.0a5-py3-none-any.whl
```
