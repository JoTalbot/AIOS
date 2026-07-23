"""HintsMessenger — generic guarded-мессенджер платформы по hints.

Тонкая платформенная обёртка (WhatsappMessenger, ViberMessenger, ...)
задаёт только package/deep-link/имя платформы; вся guarded-механика —
унаследованный outbox-контур OLXMessenger, ввод/отправка по
calibrated hints из ``extras.parser_hints.messenger`` дескриптора.
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


class HintsMessenger(OLXMessenger):
    """OLXMessenger, целиком питаемый от ``parser_hints.messenger``.

    Args:
        platform: имя платформы (для hints-резолва).
        package: android-пакет приложения.
        deep_link: URL открытия инбокса (``am start -d ...``).
        adb/storage/directory/messenger_hints/screen_width: как у
            OLXMessenger; hints None → секция ``messenger`` YAML.
    """

    def __init__(
        self,
        platform: str,
        package: str,
        deep_link: Optional[str],
        adb: Optional[ADBController] = None,
        storage=None,
        messenger_hints: Optional[Dict] = None,
        directory: str = "platforms",
        screen_width: int = 1080,
        serial: Optional[str] = None,
    ) -> None:
        super().__init__(
            adb=adb or ADBController(package=package, serial=serial),
            storage=storage,
            screen_width=screen_width,
        )
        self.platform = platform
        self.package = package
        self.deep_link = deep_link
        if messenger_hints is None:
            messenger_hints = load_hints_section(platform, "messenger", directory)
        self.messenger_hints = messenger_hints or {}
        bubbles = [
            m.get("resource_id", "").rsplit("/", 1)[-1].lower()
            for m in (self.messenger_hints.get("bubble_markers") or [])
            if isinstance(m, dict)
        ]
        threads = [
            m.get("resource_id", "").rsplit("/", 1)[-1].lower()
            for m in (self.messenger_hints.get("chat_markers") or [])
            if isinstance(m, dict)
        ]
        markers = tuple(sorted(set(threads or bubbles)))
        self._chat_parser = ChatListParser(markers=markers) if markers else None
        self._sender = HintSender(self.adb, self.messenger_hints)

    def open_chats(self) -> Dict[str, object]:
        """Открыть инбокс: deep-link или fallback-запуск приложения."""
        if self.deep_link:
            return self.adb.run(
                f"{self.adb.adb} shell am start "
                f'-a android.intent.action.VIEW -d "{self.deep_link}"'
            )
        return self.adb.run(
            f"{self.adb.adb} shell monkey -p {self.package} "
            f"-c android.intent.category.LAUNCHER 1"
        )

    def list_chats(self, dump_path: str = "chats.xml") -> List[ChatThread]:
        """Список диалогов; без калиброванных маркеров — честный []."""
        if self._chat_parser is None:
            return []
        with tempfile.TemporaryDirectory(prefix=f"aios_{self.platform}_chats_") as tmp:
            path = os.path.join(tmp, dump_path)
            self.adb.dump_ui(path)
            if not os.path.exists(path):
                return []
            return self._chat_parser.parse(path)

    def read_chat(self, thread: ChatThread, dump_path: str = "chat.xml") -> List[Message]:
        """Открытый диалог: alignment-парсер OLX (shape-based)."""
        return super().read_chat(thread, dump_path)

    def _type_and_send(self, text: str) -> Dict[str, object]:
        """Hints-driven: tap input → ADBKeyBoard → tap send/ENTER."""
        return self._sender.type_and_send(text)
