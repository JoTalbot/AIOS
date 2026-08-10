"""Клавиатуры Telegram-бота (выделено из run_telegram_bot.py)."""
from __future__ import annotations


MAIN_MENU_KEYBOARD = {
    "keyboard": [
        [{"text": "📊 Сводка"}, {"text": "🏬 Каталог"}],
        [{"text": "🆚 Конкуренты"}, {"text": "🛒 OLX"}],
        [{"text": "💼 Фриланс"}, {"text": "💰 Казначейство"}],
        [{"text": "📈 Трейдинг"}, {"text": "📦 Новая Почта"}],
        [{"text": "📲 Телефон & Банки"}, {"text": "🛡 SRE Статус"}],
        [{"text": "❓ Помощь"}, {"text": "🧭 Меню"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}


# Inline-главное меню (v22.8): красивая навигация кнопками под сообщением
MAIN_MENU_INLINE = {
    "inline_keyboard": [
        [{"text": "📊 Сводка", "callback_data": "nav_dashboard"},
         {"text": "🏬 Каталог", "callback_data": "nav_catalog"}],
        [{"text": "🆚 Конкуренты", "callback_data": "nav_competitors"},
         {"text": "🛒 OLX", "callback_data": "nav_olx"}],
        [{"text": "💼 Фриланс", "callback_data": "nav_freelance"},
         {"text": "💰 Казначейство", "callback_data": "nav_treasury"}],
        [{"text": "📈 Трейдинг", "callback_data": "nav_trading"},
         {"text": "📦 Новая Почта", "callback_data": "nav_np"}],
        [{"text": "📲 Телефон & Банки", "callback_data": "nav_phone"},
         {"text": "🛡 SRE", "callback_data": "nav_sre"}],
        [{"text": "❓ Помощь", "callback_data": "nav_help"}],
    ]
}


# Быстрые действия OLX (v22.8): кнопки под сообщением раздела
OLX_ACTIONS_INLINE = {
    "inline_keyboard": [
        [{"text": "📊 Статистика", "callback_data": "olx_stats"},
         {"text": "🆕 Последние", "callback_data": "olx_latest"}],
        [{"text": "📈 Аналитика цен", "callback_data": "olx_analytics"},
         {"text": "📋 Подписки", "callback_data": "olx_subs"}],
        [{"text": "🏬 Склад", "callback_data": "nav_catalog"}],
    ]
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

# Быстрые действия для Крипто-Заработка (5 бирж)
CRYPTO_ACTIONS_INLINE = {
    "inline_keyboard": [
        [{"text": "📊 График PnL", "callback_data": "crypto_chart"},
         {"text": "💼 Открытые позиции", "callback_data": "crypto_positions"}],
        [{"text": "⚡ Арбитраж цен", "callback_data": "nav_arb"},
         {"text": "🔄 Обновить сводку", "callback_data": "crypto_refresh"}],
    ]
}
