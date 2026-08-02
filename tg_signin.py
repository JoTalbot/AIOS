#!/usr/bin/env python3
"""
Завершение входа в личный Telegram.
  python tg_signin.py <код>            — обычный вход
  python tg_signin.py <код> <пароль2fa> — вход с 2FA
"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from telethon import TelegramClient  # noqa: E402
from telethon.errors import SessionPasswordNeededError  # noqa: E402


async def main() -> None:
    code = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    pwd = sys.argv[2].strip() if len(sys.argv) > 2 else ""
    if not code:
        print(json.dumps({"status": "error", "error": "python tg_signin.py <код> [пароль2fa]"}))
        return
    client = TelegramClient(str(ROOT / "data" / "tg_userbot"), 7758033,
                            "7c2f1819ceab23fded0dcca82af7a580")
    await client.connect()
    if await client.is_user_authorized():
        me = await client.get_me()
        print(json.dumps({"status": "already", "name": me.first_name, "id": me.id}, ensure_ascii=False))
        await client.disconnect()
        return
    try:
        await client.sign_in("+380959052288", code, phone_code_hash="cef489ed0bcaaad5d6")
    except SessionPasswordNeededError:
        if not pwd:
            print(json.dumps({"status": "need_2fa", "error": "Нужен пароль 2FA: python tg_signin.py <код> <пароль>"}))
            await client.disconnect()
            return
        try:
            await client.sign_in(password=pwd)
        except Exception as e:
            print(json.dumps({"status": "error", "error": str(e)[:300]}, ensure_ascii=False))
            await client.disconnect()
            return
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)[:300]}, ensure_ascii=False))
        await client.disconnect()
        return
    me = await client.get_me()
    print(json.dumps({"status": "ok", "name": me.first_name, "username": me.username,
                      "id": me.id}, ensure_ascii=False))
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
