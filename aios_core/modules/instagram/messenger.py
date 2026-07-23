"""Instagram Direct — guarded-мессенджер поверх OLX outbox-механики.

Наследует весь guarded-контур OLXMessenger без изменений:

* ``send_reply(auto_send=False)`` — ответ только в outbox очередь
  (ничего не уходит на устройство молча);
* ``flush_outbox()`` — отправка одобренных из очереди;
* история/статусы в ``InstagramStorage`` (общая схема outbox OLX).

Переопределено только то, что специфично для Instagram:

* ``open_chats()`` — deep-link Direct inbox;
* чтение списка чатов — ChatListParser с маркерами из
  ``parser_hints.messenger`` (bubble/thread resource-id калибровки);
* ``_type_and_send`` — :class:`HintSender`: тап по полю ввода →
  ADBKeyBoard → тап по send-маркеру (ENTER fallback).
"""

from __future__ import annotations

import os
import tempfile
from typing import Dict, List, Optional

from aios_core.modules.olx.adb import ADBController
from aios_core.modules.olx.messenger import (
    ChatListParser,
    ChatThread,
    Message,
    OLXMessenger,
)
from aios_core.platforms.runtime_hints import HintSender, load_hints_section

PACKAGE = "com.instagram.android"
DIRECT_INBOX_URL = "https://www.instagram.com/direct/inbox/"


class InstagramMessenger(OLXMessenger):
    """OLXMessenger для Instagram Direct (outbox-очередь общая).

    Args:
        adb: ADBController (с serial-привязкой профиля).
        storage: InstagramStorage для outbox (или None — только отчёты).
        messenger_hints: Секция ``parser_hints.messenger``; None → из
            дескриптора ``platforms/instagram.yaml``.
        directory: Каталог YAML-дескрипторов.
    """

    def __init__(
        self,
        adb: Optional[ADBController] = None,
        storage=None,
        messenger_hints: Optional[Dict] = None,
        directory: str = "platforms",
        screen_width: int = 1080,
        serial: Optional[str] = None,
        package: str = PACKAGE,
    ):
        super().__init__(
            adb=adb or ADBController(package=package, serial=serial),
            storage=storage,
            screen_width=screen_width,
        )
        if messenger_hints is None:
            messenger_hints = load_hints_section("instagram", "messenger", directory)
        self.messenger_hints = messenger_hints or {}
        bubbles = [
            m.get("resource_id", "").rsplit("/", 1)[-1].lower()
            for m in (self.messenger_hints.get("bubble_markers") or [])
            if isinstance(m, dict)
        ]
        # Маркеры контейнеров строк DM-инбокса (fallback — OLX-маркеры).
        self._chat_parser = ChatListParser(
            markers=tuple(sorted(b for b in bubbles if b))
        )
        self._sender = HintSender(self.adb, self.messenger_hints)

    def open_chats(self) -> Dict[str, object]:
        """Открыть Direct inbox (deep-link; установленное приложение ловит)."""
        return self.adb.run(
            f"{self.adb.adb} shell am start "
            f'-a android.intent.action.VIEW -d "{DIRECT_INBOX_URL}"'
        )

    def list_chats(self, dump_path: str = "chats.xml") -> List[ChatThread]:
        """Список диалогов Direct с маркерами калибровки."""
        with tempfile.TemporaryDirectory(prefix="aios_ig_chats_") as tmp:
            path = os.path.join(tmp, dump_path)
            self.adb.dump_ui(path)
            if not os.path.exists(path):
                return []
            return self._chat_parser.parse(path)

    def read_chat(
        self, thread: ChatThread, dump_path: str = "chat.xml"
    ) -> List[Message]:
        """Открытый диалог: наследуем alignment-парсер OLX (shape-based)."""
        return super().read_chat(thread, dump_path)

    def _type_and_send(self, text: str) -> Dict[str, object]:
        """Hints-driven executor: tap input → ADBKeyBoard → tap send/ENTER."""
        return self._sender.type_and_send(text)
