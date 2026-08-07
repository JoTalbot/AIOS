"""Клавиатуры Telegram-бота (выделено из run_telegram_bot.py)."""
from __future__ import annotations


MAIN_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "💰 Казначейство"}, {"text": "📈 Трейдинг"}],
        [{"text": "💧 Ликвидность"}, {"text": "⚡ Арбитраж"}],
        [{"text": "📱 Mesh"}, {"text": "🛒 Склад & OLX"}],
        [{"text": "📦 Новая Почта"}, {"text": "🌐 Веб-каталог"}],
        [{"text": "📲 Телефон & Банки"}, {"text": "🛡 SRE Статус"}],
        [{"text": "❓ Помощь"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}


CODER_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "📋 Статус"}, {"text": "📦 Бэклог"}],
        [{"text": "⚖️ Балансер"}, {"text": "📜 Git"}],
        [{"text": "🔍 Review Bot"}, {"text": "🔍 Review Coder"}],
        [{"text": "✨ Написать код"}, {"text": "🔧 Исправить"}],
        [{"text": "🚀 Push"}, {"text": "🔄 Перезапуск"}],
        [{"text": "◀️ Меню"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}


OLX_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "📊 OLX Стат"}, {"text": "📋 Подписки"}],
        [{"text": "🆕 Последние"}, {"text": "📈 Аналитика"}],
        [{"text": "◀️ Меню"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}


ACCOUNTS_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "🌐 Google"}, {"text": "📸 Instagram"}],
        [{"text": "📘 Facebook"}, {"text": "🎵 TikTok"}],
        [{"text": "🛒 OLX"}, {"text": "◀️ Меню"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}


PHONE_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "📲 Центр телефона"}, {"text": "🛠 Восстановление"}],
        [{"text": "📥 Лиды телефона"}, {"text": "📌 CRM задачи"}],
        [{"text": "🏦 Банки телефона"}, {"text": "📈 Тренды телефона"}],
        [{"text": "🔄 Синхронизации"}, {"text": "📋 Журнал телефона"}],
        [{"text": "🗄 Здоровье данных"}, {"text": "📦 Инвентарь"}],
        [{"text": "📤 Экспорт метрик"}, {"text": "🧩 Калибровки"}],
        [{"text": "🧪 Сценарии"}, {"text": "🚕 Маршруты"}],
        [{"text": "◀️ Меню"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}


GOOGLE_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "✉️ Непрочитанные"}, {"text": "📥 Последние письма"}],
        [{"text": "🔍 Поиск письма"}, {"text": "📧 Отправить письмо"}],
        [{"text": "👤 Кто я"}, {"text": "📅 События"}],
        [{"text": "➕ Событие"}, {"text": "📄 Документ"}],
        [{"text": "🗂 Диск"}, {"text": "📷 Скрин почты"}],
        [{"text": "◀️ Аккаунты"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}


INSTAGRAM_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "👤 Мой профиль"}, {"text": "📈 Подписчики"}],
        [{"text": "🖼 Мои посты"}, {"text": "📷 Скрин профиля"}],
        [{"text": "💬 Директ"}, {"text": "❤️ Лайкнуть"}],
        [{"text": "👤 Подписка"}, {"text": "◀️ Аккаунты"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}


BOT_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "📊 Статус бота"}, {"text": "⏸️ Пауза"}],
        [{"text": "▶️ Старт"}, {"text": "🔄 Рестарт"}, {"text": "⏹️ Стоп"}],
        [{"text": "🌐 Gemini Web"}, {"text": "🔄 Балансер"}],
        [{"text": "◀️ Меню"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}


DANGEROUS_CALLBACKS = {"coder_git_push", "coder_restart", "bot_restart", "bot_stop"}
