# WhatsApp — onboarding (alpha.21)

Onboarding-пакет: `platforms/whatsapp.yaml` +
`aios_core/modules/whatsapp/` (WhatsAppStorage, WhatsAppMessenger —
guarded HintsMessenger, WhatsAppBootstrap). Compliance:
`autopost_allowed: false`, `messenger: approval-only`,
`collector: false`.

## 1. Подготовка устройства

```bash
aios platforms fetch-apk com.whatsapp          # apkeep → apks/
adb -s <SERIAL> install apks/com.whatsapp*.apk
aios whatsapp doctor --serial <SERIAL>
```

## 2. Live-калибровка hints (on-device)

`parser_hints` честно пустые после установки — они снимаются с живого
устройства, а не выдумываются. Готовый сценарий печатает:

```bash
aios platforms doctor --platform whatsapp --calibrate-recipe
```

По шагам рецепта: откройте инбокс/чат и снимите дамп:

```bash
adb -s <SERIAL> shell uiautomator dump /sdcard/whatsapp-messenger.xml
adb -s <SERIAL> pull /sdcard/whatsapp-messenger.xml \
  platforms/whatsapp-messenger.xml
aios platforms calibrate --platform whatsapp \
  --messages platforms/whatsapp-messenger.xml --write
aios whatsapp doctor --serial <SERIAL>   # hints_messenger → ok
```

## 3. Guarded-работа

```bash
aios whatsapp chats --db data/whatsapp.sqlite
aios whatsapp dm-send --chat '<chat>' --text 'Здравствуйте!' \
  --db data/whatsapp.sqlite               # → outbox (очередь одобрения)
aios whatsapp dm-outbox --db data/whatsapp.sqlite
aios whatsapp dm-flush --db data/whatsapp.sqlite   # после одобрения
```

Ничего не отправляется в обход outbox; `--auto-send` у dm-send —
явное сознательное исключение.
