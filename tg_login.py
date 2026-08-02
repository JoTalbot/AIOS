#!/usr/bin/env python3
"""
AIOS Telegram Userbot Login — интерактивный вход в личный Telegram аккаунт.
Использует api_id/api_hash из .env (TG_API_ID, TG_API_HASH) или data/tg_config.json.
Код подтверждения придёт в Telegram/СМС — введите его здесь.

Запуск:
  python tg_login.py [phone]
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from telethon import TelegramClient  # noqa: E402
from telethon.errors import SessionPasswordNeededError  # noqa: E402


def _env(key: str) -> str:
    import os
    v = os.environ.get(key, "")
    if v:
        return v
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


async def main() -> None:
    api_id = _env("TG_API_ID")
    api_hash = _env("TG_API_HASH")
    if not api_id or not api_hash:
        print("❌ Нужны TG_API_ID и TG_API_HASH в .env (получить: my.telegram.org)")
        sys.exit(1)
    phone = sys.argv[1] if len(sys.argv) > 1 else (_env("TG_PHONE") or input("Номер телефона (с кодом страны): ").strip())

    session = str(ROOT / "data" / "tg_userbot")
    client = TelegramClient(session, int(api_id), api_hash)
    await client.connect()
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"✅ Уже авторизован: {me.first_name} @{me.username} (id={me.id})")
        await client.disconnect()
        return
    print(f"📱 Отправляю код на {phone}…")
    await client.send_code_request(phone)
    code = input("Введите код из Telegram/СМС: ").strip()
    try:
        await client.sign_in(phone, code)
    except SessionPasswordNeededError:
        pwd = input("Включена 2FA. Введите пароль: ").strip()
        await client.sign_in(password=pwd)
    me = await client.get_me()
    print(f"✅ Вход выполнен: {me.first_name} @{me.username} (id={me.id})")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
