# Signal Desktop в AIOS

## Подключение

Signal Desktop работает в VNC-дисплее `:1` и после привязки телефона доступен
через безопасный desktop adapter:

```bash
python run_account_control.py signal status
python run_account_control.py signal chats
python run_account_control.py signal read "Название чата" --limit 12
python run_account_control.py signal send "Название чата" "Текст" --confirm
```

Сервис `aios-signal-desktop.service` ждёт VNC-дисплей и запускает Signal после
перезагрузки сервера. Для Electron включён запуск с `--no-sandbox`, необходимый
для desktop-приложения под root/VNC. Сервис `aios-vnc-keepawake.service`
предотвращает блокировку/затемнение VNC, иначе OCR-адаптеры не могут читать
окна Signal и Viber.

## Единый инбокс и Telegram

Signal добавлен в общий инбокс:

- `инбокс` — включает Signal наряду с почтой, Telegram, Viber и другими каналами;
- `инбокс только Signal` — фильтр Signal;
- открытие Signal-пункта читает выбранный чат;
- `ответь на N: текст` запрашивает подтверждение перед реальной отправкой;
- `черновики Signal` — показывает ожидающие варианты ответов.

Desktop OCR не даёт достоверный unread-флаг, поэтому Signal не подменяет
«непрочитанное», а команда «всё прочитано» не открывает все Signal-чаты
массово.

## Черновики и автоответы

Фоновый сервис `aios-signal-autoreply.service` может анализировать разрешённые
чаты и создавать черновики. Каждый вариант приходит в Telegram с кнопками
**«Отправить»** / **«Отклонить»**. До нажатия кнопки текст в Signal не уходит.

Настройка в `data/platform_autoreply.json`:

```json
{
  "platforms": {
    "signal": {
      "enabled": true,
      "auto_send": false,
      "max_replies_per_run": 2,
      "allowed_chats": []
    }
  }
}
```

`allowed_chats` — allowlist фонового доступа. Пустой список не открывает чаты в
фоне, а `"*"` разрешает все чаты. Автоматическую отправку (`auto_send: true`)
следует включать только после отдельного явного решения владельца.
