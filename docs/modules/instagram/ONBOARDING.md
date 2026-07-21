# Instagram — онбординг платформы (APK → логин → калибровка → коллектор)

Платформа `instagram` (`com.instagram.android`) уже заscaffoldена в
репозитории: `platforms/instagram.yaml`, `aios_core/modules/instagram/`
(хранилище `InstagramStorage` — полная схема OLX: объявления, история
цен, outbox, свои объявления, конкуренты), login-драйв.

> ⚠️ **Секреты только через окружение.** Логин/пароль аккаунта не
> хранятся в репозитории, БД и логах — только env-переменные
> (см. `aios_core/platforms/secrets.py`).

## 0. Инструменты (на машине оператора)

```bash
cargo install apkeep           # загрузка APK (APKPure/Google Play/F-Droid)
# Android SDK: aapt (build-tools), adb, эмулятор (cmdline-tools)
```

## 1. Секреты аккаунта

```bash
export AIOS_SECRET__INSTAGRAM__USERNAME='jo.talbot@gmail.com'
export AIOS_SECRET__INSTAGRAM__PASSWORD='•••'
# или файл data/secrets.env (в .gitignore):
#   AIOS_SECRET__INSTAGRAM__USERNAME=...
#   AIOS_SECRET__INSTAGRAM__PASSWORD=...
```

Профильные аккаунты: `AIOS_SECRET__INSTAGRAM__<ПРОФИЛЬ>__PASSWORD`.

## 2. Скачать APK (автоматически)

```bash
aios platforms fetch-apk com.instagram.android
# apks/com.instagram.android.apk (источник по умолчанию — APKPure)
```

## 3. Запустить эмулятор и установить APK

```bash
aios devices ensure --profile instagram:main
adb -s emulator-5554 install apks/com.instagram.android.apk
aios profiles add --platform instagram --name main \
    --device emulator-5554 --default
```

## 4. Калибровка с логином (E2E через bootup)

Instagram закрывает ленту стеной входа — используется login-драйв,
который вводит env-секреты в форму (TAB/ENTER, без координат):

```python
from aios_core.modules.instagram import InstagramLoginDriver
from aios_core.platforms import bootup_platform

drv = InstagramLoginDriver(serial="emulator-5554")
report = bootup_platform(
    apk_path="com.instagram.android", fetch=True,
    driver=drv.drive, query="sneakers",
)
print(report["status"], report["steps"]["verify"])
```

После `status == "ready"`: `extras.parser_hints` в
`platforms/instagram.yaml` + скомпилированный
`aios_core/modules/instagram/card_parser.py` (маркеры Instagram-ленты).

## 5. Эксплуатация

- Дрейф верстки после обновлений приложения:
  `aios platforms marker-check --platform instagram --dump feed.xml`
  → `drift` ⇒ `calibrate --write` + `codegen --force`.
- Детальный экран и диалоги:
  `aios platforms calibrate --platform instagram --dump feed.xml
  --detail post.xml --messages dm.xml --write`.
- Профили/пул/шардинг — общие механизмы `aios_core/platforms/`
  (каждый аккаунт = профиль со своим ADB-serial и своей БД).

## Статус на момент v9.0.0-alpha.12

В CI-песочнице нет Android SDK/эмулятора и сети для загрузки APK —
реальная калибровка (`steps.calibrate`) выполняется на машине
оператора по шагам выше. Все переходы пайплайна покрыты тестами с
инъецированными runner'ами; login-драйв проверен на синтетических
дампах стены входа/ленты.
