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

## 5. Эксплуатация (полный функционал)

CLI-группа `aios instagram`:

```bash
aios instagram doctor [--serial emulator-5554]      # готовность: adb/
                                                    # секреты/маркеры
aios instagram collect --query "кросівки" --db data/instagram.sqlite \
    [--serial E] [--login]          # сбор карточек ленты/выдачи
aios instagram login-drive --query "кросівки" --serial E   # за стену
                                                           # входа → дамп
aios instagram dm-send --chat chat:anna --text "..." --db D   # в outbox
aios instagram dm-send ... --auto-send      # немедленная отправка
aios instagram dm-outbox --db D             # очередь ответов
aios instagram dm-flush --db D              # отправить одобренные

# AutoWatch: цикл заботы (подписки → алерты → свои → застой → план)
aios platforms autowatch --platform instagram --profile main \
    --query "кросівки" [--webhook URL] [--drive login]

# REST (aios run): те же guarded-механики
# GET  /api/v1/modules/instagram/chats?profile=main
# GET  /api/v1/modules/instagram/outbox?profile=main
# POST /api/v1/modules/instagram/outbox/send   {"chat_key","text"}
# POST /api/v1/modules/instagram/outbox/flush

# Свои посты: снапшот счётчиков + guarded-публикация (DRY-RUN!)
aios instagram own --db data/instagram.sqlite [--dump grid.xml]
aios instagram post --image photo.jpg --text "Нові кросівки!"      # план
aios instagram post --image photo.jpg --text "..." --confirm       # публикация

# Видео-контент (Reels): HintVideoParser/video_parser_for —
# подпись/тайм-код/просмотры/лайки по video-маркерам калибровки

# Автоматизация: циклы заботы всех профилей на арендованных устройствах
aios devices fleet-run --every-s 900 [--query "кросівки"] [--webhook URL]
```

Модули:

- `InstagramCollector` — движок OLXCollector (дамп→парсер→свайп→дедуп),
  навигация через login/point-драйв, парсер из дескриптора;
- `InstagramDetailParser` — открытый пост: цена/продавец/CTA/описание
  из hints-detail;
- `InstagramMessenger` — **guarded Direct**: ответы по умолчанию только
  в outbox-очередь (`InstagramStorage`), на устройство — после
  `dm-flush`/`--auto-send`; ввод/отправка по send/ввод-маркерам;
- `InstagramBootstrap.doctor()` — отчёт готовности (значения секретов
  не отчитываются, только наличие переменных).

- Дрейф верстки после обновлений приложения:
  `aios platforms marker-check --platform instagram --dump feed.xml`
  → `drift` ⇒ `calibrate --write` + `codegen --force`
  (шаблонные cron-строки: `aios cron-plan --with-marker-check`).
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
