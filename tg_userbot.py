#!/usr/bin/env python3
"""
AIOS Telegram Userbot — личный Telegram аккаунт (не бот) через Telethon.
Доступ к личным чатам, ботам, отправка сообщений от имени пользователя.

Функции (run_account_control.py):
  tg dialogs [N]      — список последних диалогов (чаты/боты)
  tg read <id|name>   — прочитать последние сообщения диалога
  tg send <id|name> <text> [--confirm] — отправить сообщение
  tg bot <bot_username> <command> [--confirm] — команда боту + чтение ответа

Сессия: data/tg_userbot.session (создаётся скриптом tg_login.py)
Конфиг: api_id/api_hash/phone из .env (TG_API_ID, TG_API_HASH, TG_PHONE)
или из data/tg_config.json
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from telethon import TelegramClient  # noqa: E402


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


def _cfg() -> dict:
    cfg_path = ROOT / "data" / "tg_config.json"
    cfg = {}
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
        except Exception:
            cfg = {}
    cfg.setdefault("api_id", _env("TG_API_ID"))
    cfg.setdefault("api_hash", _env("TG_API_HASH"))
    cfg.setdefault("phone", _env("TG_PHONE"))
    return cfg


async def _client() -> TelegramClient:
    cfg = _cfg()
    api_id = str(cfg.get("api_id") or "").strip()
    api_hash = str(cfg.get("api_hash") or "").strip()
    if not api_id or not api_hash:
        raise RuntimeError(
            "Нет TG_API_ID/TG_API_HASH. Получите на my.telegram.org и добавьте в .env "
            "или data/tg_config.json, затем запустите tg_login.py для входа")
    session = str(ROOT / "data" / "tg_userbot")
    client = TelegramClient(session, int(api_id), api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("Не авторизован. Запустите tg_login.py для входа (код из Telegram)")
    return client


async def dialogs(limit: int = 15) -> dict:
    client = await _client()
    try:
        out = []
        async for d in client.iter_dialogs(limit=limit):
            entity = d.entity
            is_bot = getattr(entity, "bot", False) if hasattr(entity, "bot") else False
            out.append({
                "id": d.id,
                "name": d.name or "(без названия)",
                "is_bot": bool(is_bot),
                "unread": d.unread_count,
                "last_msg": (d.message.message or "")[:80] if d.message else "",
            })
        return {"status": "ok", "dialogs": out, "count": len(out)}
    finally:
        await client.disconnect()


async def _resolve(client, ref: str):
    """Разрешить 'id' или 'имя' в объект диалога."""
    ref = str(ref).strip()
    if ref.isdigit():
        return await client.get_entity(int(ref))
    # попробовать по username / имени
    try:
        if ref.startswith("@"):
            return await client.get_entity(ref)
    except Exception:
        pass
    async for d in client.iter_dialogs(limit=200):
        if d.name and d.name.lower() == ref.lower():
            return d.entity
    try:
        return await client.get_entity(ref)
    except Exception:
        pass
    raise ValueError(f"Диалог «{ref}» не найден")


async def read_dialog(ref: str, limit: int = 12) -> dict:
    client = await _client()
    try:
        entity = await _resolve(client, ref)
        msgs = []
        async for m in client.iter_messages(entity, limit=limit):
            sender = ""
            try:
                if m.sender_id:
                    sender_ent = await client.get_entity(m.sender_id)
                    sender = getattr(sender_ent, "first_name", "") or getattr(sender_ent, "title", "") or str(m.sender_id)
            except Exception:
                sender = str(m.sender_id) if m.sender_id else ""
            text = (m.message or "")[:300]
            msgs.append({"from": sender, "text": text, "out": bool(m.out),
                         "date": str(m.date)[:16] if m.date else ""})
        return {"status": "ok", "dialog": ref, "messages": msgs}
    finally:
        await client.disconnect()


async def send_msg(ref: str, text: str, confirm: bool) -> dict:
    if not confirm:
        return {"status": "need_confirm", "action": "tg_send", "dialog": ref,
                "text": text[:200]}
    client = await _client()
    try:
        entity = await _resolve(client, ref)
        await client.send_message(entity, text)
        return {"status": "sent", "dialog": ref, "text": text[:200]}
    finally:
        await client.disconnect()


async def bot_command(bot: str, command: str, confirm: bool) -> dict:
    if not confirm:
        return {"status": "need_confirm", "action": "tg_bot",
                "bot": bot, "command": command[:200]}
    client = await _client()
    try:
        entity = await client.get_entity(bot)
        await client.send_message(entity, command)
        await asyncio.sleep(3)  # ждём ответ бота
        msgs = []
        async for m in client.iter_messages(entity, limit=5):
            msgs.append({"from": "бот" if m.out is False else "я", "text": (m.message or "")[:300],
                         "out": bool(m.out)})
        return {"status": "ok", "bot": bot, "command": command, "reply": msgs[:3]}
    finally:
        await client.disconnect()


async def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "dialogs"
    try:
        if action == "dialogs":
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 15
            print(json.dumps(await dialogs(n), ensure_ascii=False, default=str))
        elif action == "read":
            ref = sys.argv[2]
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 12
            print(json.dumps(await read_dialog(ref, limit), ensure_ascii=False, default=str))
        elif action == "send":
            ref, text = sys.argv[2], sys.argv[3]
            confirm = "--confirm" in sys.argv
            print(json.dumps(await send_msg(ref, text, confirm), ensure_ascii=False, default=str))
        elif action == "bot":
            bot, command = sys.argv[2], sys.argv[3]
            confirm = "--confirm" in sys.argv
            print(json.dumps(await bot_command(bot, command, confirm), ensure_ascii=False, default=str))
        else:
            print(json.dumps({"status": "error", "error": f"Неизвестная команда {action}"}))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)[:400]}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
