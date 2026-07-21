# AIOS v9.0.0-alpha.12 — ApkFetch + Secrets + Instagram: онбординг второй платформы

**Дата:** 2026-07-21 · **Тесты:** 789 passing (+29)

Первая вторая платформа подключена к AIOS: **Instagram**
(`com.instagram.android`) — со scaffold-модулем, хранилищем и
login-драйвом за стену входа. Пайплайн bootup теперь сам скачивает
APK и сам берёт устройство из пула; учётные данные — только через
env-переменные.

## Что нового

### ApkFetch — пайплайн сам находит и скачивает APK
Обёртка над [`apkeep`](https://github.com/EFForg/apkeep)
(APKPure/Google Play/F-Droid без аккаунта):

```bash
aios platforms fetch-apk com.instagram.android
aios platforms bootup --apk com.instagram.android --fetch
```

`resolve_apk`: существующий `.apk` → кеш `apks/` (переиспользуется) →
скачивание по имени пакета (только с `--fetch`). Runner инъецируется,
ошибки честные (нет apkeep/сети → подсказка по установке).

### Secrets — пароли никогда в коде/БД/логах
`platforms/secrets.py`: `AIOS_SECRET__<PLATFORM>__<FIELD>` и профильные
`AIOS_SECRET__<PLATFORM>__<PROFILE>__<FIELD>` (приоритет); loader
`data/secrets.env` (в `.gitignore`) без затирания окружения; ошибки
называют переменную, не значение. Для Instagram:

```bash
export AIOS_SECRET__INSTAGRAM__USERNAME='jo.talbot@gmail.com'
export AIOS_SECRET__INSTAGRAM__PASSWORD='•••'
```

### Instagram — боевой онбординг второй платформы
- `platforms/instagram.yaml` + `aios_core/modules/instagram/`:
  `InstagramStorage` (полная схема OLX) + дескриптор в каталоге;
- `InstagramLoginDriver`: Instagram закрывает ленту стеной входа —
  драйв детектирует логин-экран по маркерам, вводит env-секреты
  (TAB/ENTER keyevents, без координат), честно падает, если стена не
  пройдена (верификация/смена верстки);
- пошаговый онбординг: `docs/modules/instagram/ONBOARDING.md`.

### Калибровка детального экрана и мессенджера
`DetailCalibrationAdvisor`: price/seller/CTA/описание для экрана
объявления; EditText/кнопка отправки/пузыри для переписки;
`merge_hints` складывает секции `detail`/`messenger` в
`extras.parser_hints`. CLI: `calibrate --detail post.xml
--messages dm.xml --write`.

### Marker drift — защита от обновлений верстки
`platforms/regression.py`: `check_platform_markers(platform, dump)`
сравнивает baseline-маркеры дескриптора со свежей калибровкой →
`ok`/`drift`/`no-baseline`; при drift — рецепт рекалибровки
(`calibrate --write && codegen --force`). CLI `marker-check`.

### Bootup + DevicePool
`--serial` (прямая привязка) или `--lease` — аренда устройства из пула
под ключ `<platform>:calibration` с авто-release после драйва;
драйв получает serial; очередь/pool semantics переиспользуются.
Толерантность stub-APK при инъецированном aapt-runner сохранена.

## Установка

```bash
pip install aios-9.0.0a12-py3-none-any.whl
```

## Дальше (дорожная карта к 10000+)

- Codegen `detail.py`/`messenger.py` из секций hints (шаблоны = OLX).
- Point-драйвы поиска: калибровщик сам находит поисковую строку.
- Marker-check в cron-plan: авто-re-calibrate + drift-алёрты по всему
  каталогу платформ.
