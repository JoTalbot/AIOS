# Viber — onboarding (alpha.21)

Onboarding-пакет: `platforms/viber.yaml` + `aios_core/modules/viber/`
(ViberStorage, ViberMessenger — guarded HintsMessenger с deep-link
`viber://chats`, ViberBootstrap). Compliance: `autopost_allowed: false`,
`messenger: approval-only`, `collector: false`.

## 1. Установка

```bash
aios platforms fetch-apk com.viber.voip
adb -s <SERIAL> install apks/com.viber.voip*.apk
aios viber doctor --serial <SERIAL>
```

## 2. Live-калибровка hints

```bash
aios platforms doctor --platform viber --calibrate-recipe
```

Откройте чаты экрана Viber, снимите дамп и запишите маркеры:

```bash
adb -s <SERIAL> shell uiautomator dump /sdcard/viber-messenger.xml
adb -s <SERIAL> pull /sdcard/viber-messenger.xml \
  platforms/viber-messenger.xml
aios platforms calibrate --platform viber \
  --messages platforms/viber-messenger.xml --write
aios viber doctor --serial <SERIAL>   # hints_messenger → ok
```

## 3. Guarded-работа

```bash
aios viber chats --db data/viber.sqlite
aios viber dm-send --chat '<chat>' --text 'Текст' --db data/viber.sqlite
aios viber dm-outbox --db data/viber.sqlite
aios viber dm-flush --db data/viber.sqlite
```

Все отправки — только через очередь одобрения (outbox).
