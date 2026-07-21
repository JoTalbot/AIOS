# Facebook Marketplace — onboarding (alpha.21)

OLX-like onboarding-пакет: `platforms/facebook.yaml` +
`aios_core/modules/facebook/` (FacebookStorage, FacebookMessenger —
deep-link `fb://messaging`, FacebookBootstrap). Compliance:
`autopost_allowed: false`, `messenger: approval-only`,
`collector: true` (сбор публичной ленты read-only).

## 1. Установка

```bash
aios platforms fetch-apk com.facebook.katana
adb -s <SERIAL> install apks/com.facebook.katana*.apk
aios facebook doctor --serial <SERIAL>
```

## 2. Live-калибровка hints (полный стек)

```bash
aios platforms doctor --platform facebook --calibrate-recipe
```

Маркетплейс-стек требует четыре поверхности:

```bash
# лента карточек Marketplace
adb -s <SERIAL> shell uiautomator dump /sdcard/facebook-cards.xml
# экран лота (цена/продавец/CTA)
adb -s <SERIAL> shell uiautomator dump /sdcard/facebook-detail.xml
# инбокс Messenger
adb -s <SERIAL> shell uiautomator dump /sdcard/facebook-messenger.xml
# главный экран (tab-bar)
adb -s <SERIAL> shell uiautomator dump /sdcard/facebook-navigation.xml
adb -s <SERIAL> pull /sdcard/ platforms/facebook-dumps/

aios platforms calibrate --platform facebook \
  --dump platforms/facebook-dumps/facebook-cards.xml \
  --detail platforms/facebook-dumps/facebook-detail.xml \
  --messages platforms/facebook-dumps/facebook-messenger.xml \
  --navigation platforms/facebook-dumps/facebook-navigation.xml --write
aios platforms marker-check --platform facebook \
  --dump platforms/facebook-dumps/facebook-cards.xml
aios facebook doctor --serial <SERIAL>   # cards+messenger → ok
```

## 3. Guarded-работа

```bash
aios facebook chats --db data/facebook.sqlite
aios facebook dm-send --chat '<chat>' --text 'Здравствуйте!' \
  --db data/facebook.sqlite
aios facebook dm-outbox --db data/facebook.sqlite
aios facebook dm-flush --db data/facebook.sqlite
```

Автопостинга нет (ToS Meta); лента/read-receipts — read-only,
ответы — только через очередь одобрения.
