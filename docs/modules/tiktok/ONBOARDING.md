# TikTok — onboarding (alpha.21)

Onboarding-пакет: `platforms/tiktok.yaml` + `aios_core/modules/tiktok/`
(TikTokStorage, TikTokMessenger, TikTokBootstrap). Compliance:
`autopost_allowed: false`, `messenger: approval-only`,
`collector: true` — платформа участвует в generic ReelsCollector
(reels-драйвер) после калибровки видео-ленсты.

## 1. Установка

```bash
aios platforms fetch-apk com.zhiliaoapp.musically
adb -s <SERIAL> install apks/com.zhiliaoapp.musically*.apk
aios platforms doctor --platform tiktok --serial <SERIAL>
```

## 2. Live-калибровка hints (видео-лента + tab-bar)

```bash
aios platforms doctor --platform tiktok --calibrate-recipe
```

Снимите дампы главного экрана (tab-bar) и ленты:

```bash
adb -s <SERIAL> shell uiautomator dump /sdcard/tiktok-navigation.xml
adb -s <SERIAL> pull /sdcard/tiktok-navigation.xml platforms/
adb -s <SERIAL> shell uiautomator dump /sdcard/tiktok-cards.xml
adb -s <SERIAL> pull /sdcard/tiktok-cards.xml platforms/
aios platforms calibrate --platform tiktok \
  --dump platforms/tiktok-cards.xml \
  --navigation platforms/tiktok-navigation.xml --write
aios platforms marker-check --platform tiktok \
  --dump platforms/tiktok-cards.xml     # baseline для drift-регрессии
```

## 3. Сбор видео-ленсты (read-only)

```bash
aios platforms reels --platform tiktok --db data/tiktok.sqlite --max 50
# или с авто-переходом на таб reels и webhook-алёртами:
aios platforms reels --platform tiktok --open-tab \
  --webhook http://127.0.0.1:9999/hook
```

Сбор публичного контента read-only; Direct/guarded-мессенджер — после
калибровки `parser_hints.messenger`, отправки только через outbox.
