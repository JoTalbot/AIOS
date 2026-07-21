# OLX Parser Agent — Запуск на живому пристрої

Дата: 2026-07-21. Ціль: телефон із OLX (`ua.slando`) + машина з ADB.

---

## 1. Підготовка пристрою

1. Увімкніть **Параметри розробника** → **Налагодження USB**.
2. Підключіть телефон і перевірте:

```bash
adb devices           # пристрій має бути "device", не "unauthorized"
```

3. Встановіть OLX і увійдіть у свій акаунт (session для переписки та
   «Мої оголошення» має бути активним).

## 2. Кирилиця у `adb shell input text`

Стандартний `input text` не вводить кирилицю. Встановіть
[ADBKeyBoard](https://github.com/senzhk/ADBKeyBoard):

```bash
adb install ADBKeyBoard.apk
adb shell ime set com.android.adbkeyboard/.AdbIME
```

Відправка тексту тоді робиться через broadcast, а не `input text`.
Після роботи поверніть звичну клавіатуру:
`adb shell ime set <попередній IME>`.

## 3. Калібрування (одноразово)

UI OLX змінюється між версіями, тому координатні сценарії треба звірити:

```bash
adb shell uiautomator dump /sdcard/ui.xml && adb pull /sdcard/ui.xml
aios olx detail --xml ui.xml          # перевірка парсера сторінки
aios olx own --xml ui.xml --db olx.sqlite   # з екрана «Мої оголошення»
```

Якщо координати кнопок відрізняються — підставте свої у
`OLXMessenger`/`Reposter` (мітки `*_LABELS`).

## 4. Типовий робочий цикл

```bash
# Разовий збір за запитом
aios olx collect --query "лобове скло" --max-cards 100 --db olx.sqlite

# Підписка на нові оголошення з фільтром
aios olx subscribe --query "лобове скло" --max-price 8000 --city "Дніпро"

# Снапшот своїх оголошень (екран «Мої оголошення» має бути відкритий)
adb shell am start -a android.intent.action.VIEW -d "https://www.olx.ua/"
# ... перейдіть у «Мої оголошення», далі:
adb shell uiautomator dump /sdcard/ui.xml && adb pull /sdcard/ui.xml
aios olx own --xml ui.xml --db olx.sqlite

# Застояні оголошення, покращення, план перевикладання
aios olx own --stagnant --db olx.sqlite
aios olx improve --fingerprint <fp> --query "лобове скло" --db olx.sqlite
aios olx repost   --fingerprint <fp> --db olx.sqlite          # dry-run план
# aios olx repost --fingerprint <fp> --confirm                # виконання

# Повний автоматичний цикл + сповіщення в Telegram
aios olx autowatch \
  --query "лобове скло" \
  --webhook "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  --chat-id "<CHAT_ID>" --db olx.sqlite
```

## 5. Періодика (cron)

```cron
# щогодини — збір і автодогляд, лог у /tmp/olx_watch.log
0 * * * *  cd /home/user/AIOS && /usr/bin/python3 aios_cli.py olx autowatch --query "лобове скло" --webhook "https://api.telegram.org/bot<TOKEN>/sendMessage" --chat-id "<CHAT_ID>" --db /home/user/olx.sqlite >> /tmp/olx_watch.log 2>&1
```

Альтернатива — тривалий процес із REST API:
`AIOS_OLX_DB=/home/user/olx.sqlite python3 run_rest_api.py` +
`POST /api/v1/modules/olx/schedule` (інтервал ≥ 10 с).

## 6. Telegram-сповіщення

1. `@BotFather` → `/newbot` → токен.
2. Напишіть боту, далі `https://api.telegram.org/bot<TOKEN>/getUpdates` →
   візьміть `chat.id`.
3. Webhook URL уже сумісний із `WebhookNotifier` (payload автоматично
   конвертується в `sendMessage`).

## 7. Межі та правила безпеки

- **Відповіді в чатах** завжди проходять через outbox: без `auto_send` /
  флаша нічого не відправляється.
- **Перевикладання** — тільки з `--confirm`; може суперечити правилам OLX
  щодо дублів. Бажаний варіант — спочатку `olx own edit` (редагування без
  зміни id оголошення).
- Парсери терпимі до Jetpack Compose, але перевіряйте їх після оновлень OLX.

## 8. Troubleshooting

| Проблема | Рішення |
|---|---|
| `unauthorized` у adb | Підтвердіть RSA-діалог на телефоні |
| Кирилиця → `????` | Перевірте `ime list` — має бути AdbIME |
| Порожня видача карток | Екран заблокований/застосунок згорнувся; розблокуйте й повторіть |
| Координати не спрацьовують | Оновіть мітки `*_LABELS` під поточну версію OLX |
