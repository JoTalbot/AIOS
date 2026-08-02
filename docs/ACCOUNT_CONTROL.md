# Управление Google и Instagram через диалог в Telegram

Бот AIOS (`run_telegram_bot.py`) умеет управлять вашими **Google** и **Instagram**
аккаунтами обычным «человеческим» текстом в чате — без команд и без знания API.

## Как это работает

1. Вы пишете боту естественную фразу, например: «проверь мою почту».
2. Бот распознаёт намерение (Google или Instagram) и запускает хелпер
   `run_account_control.py` (под `xvfb-run` для браузерных операций).
3. Хелпер выполняет действие через **Chrome Twin** (ваш профиль в Chrome,
   где залогинены Google `jo.talbot@gmail.com` и Instagram `@jo.talbot`),
   а для почты — надёжно через **IMAP/SMTP** (Google app password из `.env`).
4. Бот отвечает текстом и, если нужно, присылает **скриншот** (фото в чат).

## Примеры фраз

### Google
| Фраза | Что произойдёт |
|---|---|
| «проверь мою почту» | последние 5 писем (тема, отправитель, сниппет) |
| «сколько непрочитанных» | непрочитанные письма |
| «кто я в гугле» | какой Google-аккаунт залогинен в Chrome |
| «покажи календарь» | скриншот Google Календаря |
| «покажи диск» | скриншот Google Диска |
| «покажи почту» (скрин) | скриншот входящих Gmail |
| «отправь письмо ivan@gmail.com, тема Встреча, текст: привет» | подготовка письма + подтверждение |
| «да» (после подтверждения) | письмо отправлено |

### Instagram
| Фраза | Что произойдёт |
|---|---|
| «покажи мой инстаграм» | профиль: имя, подписчики, подписки, посты + скрин |
| «сколько у меня подписчиков» | то же (статистика) |
| «мои посты» | последние посты |
| «скрин моего инстаграма» | фото профиля |
| «пост /p/CODE/» | детали поста (подпись, лайки) + скрин |

## Команды и меню
- `/accounts` — меню аккаунтов (кнопки Google / Instagram)
- `/google [whoami|unread|list|calendar|drive|mailshot|send]`
- `/instagram [profile|stats|posts|screenshot]`
- Кнопки в меню «🌐 Аккаунты» в главном меню бота.

## Архитектура

```
Telegram message
   │  free text
   ▼
_handle_account_intent()          # распознавание намерения (ключевые слова)
   │
   ├── Google
   │     ├── почта: run_account_control.py google gmail_list|gmail_send
   │     │        (IMAP/SMTP + Google app password из .env)
   │     └── сервисы/скрины: run_account_control.py google whoami|screenshot <svc>
   │              (Chrome Twin: системный Google Chrome + профиль data/chrome_twin/default)
   │
   └── Instagram
         └── run_account_control.py instagram profile|posts|post|screenshot
              (InstagramChromeTwinAdapter: сессия в том же профиле Chrome)
```

- Письма читаются/отправляются через **IMAP/SMTP** (`imap.gmail.com:993`,
  `smtp.gmail.com:465`) — это надёжно и не зависит от DOM Gmail.
- Скриншоты сервисов и Instagram — через браузер под `xvfb-run -a`
  (Instagram и Google блокируют headless-браузеры).
- Все операции **read-only** для Instagram (ToS), отправка писем — только
  после явного подтверждения «да».
- Один браузер за раз; хелпер чистит lock-файлы профиля перед запуском.

## Тесты
```bash
cd /root/AIOS && source /opt/aios/.venv/bin/activate
python -m pytest tests/test_account_control_dialog.py -v
```

## Файлы
- `run_account_control.py` — хелпер (Google + Instagram), вызывается ботом
- `run_telegram_bot.py` — диалог, кнопки, отправка фото (`send_photo`)
- `aios_core/platforms/instagram_chrome_twin_adapter.py` — Instagram-адаптер
- `aios_core/platforms/chrome_twin_adapter.py` — Chrome Twin (Google)
