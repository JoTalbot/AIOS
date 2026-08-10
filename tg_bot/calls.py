"""
AIOS Telegram Bot — Модуль управления транскрибацией телефонных звонков (Whisper Colab)
"""

import os
import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aios_core.whisper_colab_transcriber import (
    check_colab_whisper_health,
    get_colab_whisper_url,
    process_calls_directory,
    CALLS_DIR
)


def _handle_calls_intent(api, chat_id: int, text: str) -> bool:
    """Обрабатывает запросы пользователя, связанные со звонками и Whisper."""
    t_lower = (text or "").lower().strip()

    keywords = ["звонок", "звонки", "whisper", "транскрипц", "расшифруй", "/calls", "аудиозапис", "trycloudflare"]

    # 0. Авто-регистрация ссылки trycloudflare.com
    if "trycloudflare.com" in t_lower:
        import re
        match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', text)
        if match:
            tunnel_url = match.group(0)
            from scripts.register_colab_whisper import register_whisper_endpoint
            api.send_message(chat_id, f"📡 Проверяю связь с Colab Whisper GPU по адресу:\n`{tunnel_url}`...", parse_mode="Markdown")
            success = register_whisper_endpoint(tunnel_url)
            if success:
                msg = (
                    f"🎉 **Google Colab Whisper GPU успешно зарегистрирован!**\n\n"
                    f"🟢 **Статус**: ONLINE\n"
                    f"🔗 **URL**: `{tunnel_url}`\n"
                    f"🧠 **Модель**: `Whisper Large-v3 (T4 GPU)`\n\n"
                    f"Теперь нажмите **`🎙️ Обработать все звонки`** для старта расшифровки!"
                )
            else:
                msg = f"❌ Не удалось подключиться к Whisper по адресу `{tunnel_url}`. Проверьте, запущены ли все ячейки в Colab."
            keyboard = _calls_keyboard()
            api.send_message(chat_id, msg, reply_markup=keyboard, parse_mode="Markdown")
            return True
    if not any(k in t_lower for k in keywords):
        return False

    # 1. Проверка команды статуса
    if "статус" in t_lower or "провер" in t_lower:
        status = check_colab_whisper_health()
        if status.get("online"):
            msg = (
                f"🟢 **Google Colab Whisper GPU — ONLINE**\n\n"
                f"🔗 **URL**: `{status.get('url')}`\n"
                f"🧠 **Модель**: `{status.get('model', 'large-v3')}` (T4 GPU FP16)\n"
                f"💳 **Тариф**: 100% Free Colab Tier\n\n"
                f"Готов к мгновенной транскрибации звонков из папки `Calls/`!"
            )
        else:
            msg = (
                f"🔴 **Google Colab Whisper GPU — OFFLINE**\n\n"
                f"Причина: `{status.get('reason', 'Нет соединения')}`\n\n"
                f"💡 **Инструкция для бесплатного запуска**:\n"
                f"1. Откройте ноутбук `docs/AIOS_Google_Colab_Whisper_Transcriber.ipynb` в Google Colab.\n"
                f"2. Выберите тип среды `T4 GPU` и выполните все ячейки.\n"
                f"3. Выполните команду регистрации: `python3 scripts/register_colab_whisper.py <url>`\n\n"
                f"*(При офлайне будет использован локальный CPU fallback)*"
            )
        keyboard = _calls_keyboard()
        api.send_message(chat_id, msg, reply_markup=keyboard, parse_mode="Markdown")
        return True

    # 2. Попытка обработки всех звонков
    if any(k in t_lower for k in ["обработай", "расшифруй", "запусти", "транскрибируй", "все"]):
        api.send_message(chat_id, "⏳ **Запуск транскрибации звонков...**\n*Проверка Colab GPU и анализ аудизаписей...*", parse_mode="Markdown")
        try:
            from scripts.sync_gdrive_calls import sync_gdrive
            sync_gdrive()
        except Exception as _ge:
            print(f"GDrive sync note: {_ge}")
        results = process_calls_directory()

        if not results:
            msg = (
                f"📁 **В папке `Calls/` нет новых необработанных аудиозаписей.**\n\n"
                f"Загрузите `.mp3`, `.wav` или `.m4a` файлы в папку `/root/AIOS/Calls/` и нажмите **`🎙️ Обработать звонки`**."
            )
        else:
            msg = f"🎉 **Успешно обработано {len(results)} новых звонков!**\n\n"
            for r in results[:3]:
                fname = r.get("filename", "Call")
                dur = r.get("duration_seconds", 0)
                summary = r.get("summary", "")[:250]
                msg += f"📞 **{fname}** ({dur} сек):\n{summary}\n---\n"

        keyboard = _calls_keyboard()
        api.send_message(chat_id, msg, reply_markup=keyboard, parse_mode="Markdown")
        return True

    # 3. Дефолтный ответ по звонкам (обзор папки)
    files = [f for f in CALLS_DIR.iterdir() if f.is_file() and f.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".opus", ".3gp", ".amr"}] if CALLS_DIR.exists() else []

    status = check_colab_whisper_health()
    gpu_badge = "🟢 ONLINE (Whisper Large-v3 T4 GPU)" if status.get("online") else "🔴 OFFLINE (Local CPU Fallback)"

    msg = (
        f"🎙️ **Модуль Транскрибации Звонков (AIOS Calls Brain)**\n\n"
        f"⚙️ **Движок**: {gpu_badge}\n"
        f"📂 **Папка звонков**: `/root/AIOS/Calls`\n"
        f"📊 **Аудиофайлов в папке**: `{len(files)}` шт.\n\n"
        f"Нажмите кнопку ниже для старта расшифровки звонков и сбора AI-аналитики!"
    )
    keyboard = _calls_keyboard()
    api.send_message(chat_id, msg, reply_markup=keyboard, parse_mode="Markdown")
    return True


def _calls_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "🎙️ Обработать все звонки", "callback_data": "call_process_all"},
                {"text": "📊 Статус Colab GPU", "callback_data": "call_status"}
            ],
            [
                {"text": "📁 Список файлов звонков", "callback_data": "call_list"}
            ]
        ]
    }
