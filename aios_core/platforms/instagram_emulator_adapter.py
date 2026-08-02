"""
Instagram Emulator Adapter — полная автоматизация Instagram через Android эмулятор
Использует ADB + UIAutomator для управления приложением com.instagram.android

Функции:
- Автологин через env секреты (AIOS_SECRET__INSTAGRAM__USERNAME/PASSWORD)
- Сбор ленты/feed и Reels через ReelsCollector
- Direct сообщения: list_chats, read_chat, send_message (guarded outbox)
- Создание постов: PostComposer + OwnPostsParser
- Парсинг профилей и постов
- Интеграция с DevicePool и ProfileStore

Архитектура как OLX, но для Instagram
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List
from pathlib import Path

from .base import IncomingMessage, PlatformAdapter, SentMessage

try:
    from aios_core.modules.instagram import (
        InstagramCollector,
        InstagramMessenger,
        InstagramStorage,
        InstagramLoginDriver,
        PostComposer,
        OwnPostsParser,
    )
    from aios_core.modules.olx.adb import ADBController
    from aios_core.platforms import get_platform
    from aios_core.platforms.reelscout import ReelsCollector
    from aios_core.android_rpa_bridge import AndroidRPADeviceEmulator
    HAS_EMULATOR = True
except ImportError as e:
    print(f"Instagram emulator dependencies missing: {e}")
    HAS_EMULATOR = False


class InstagramEmulatorAdapter(PlatformAdapter):
    """
    Instagram адаптер для Android эмулятора
    Работает через ADB/UIAutomator, не требует Graph API токенов
    Требует запущенный эмулятор с установленным com.instagram.android
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config or {})
        self.serial = self.config.get("serial") or os.getenv("ANDROID_SERIAL") or "emulator-5554"
        self.profile = self.config.get("profile") or os.getenv("AIOS_PROFILE") or "default"
        self.package = "com.instagram.android"
        
        # Emulator components
        self.adb = None
        self.storage = None
        self.messenger = None
        self.collector = None
        self.login_driver = None
        self.rpa_emulator = None
        
        if HAS_EMULATOR:
            try:
                self.adb = ADBController(package=self.package, serial=self.serial)
                # Storage per profile
                db_path = self.config.get("db_path") or f"data/instagram/{self.profile}.sqlite"
                self.storage = InstagramStorage(db_path)
                self.messenger = InstagramMessenger(adb=self.adb, storage=self.storage, serial=self.serial)
                self.login_driver = InstagramLoginDriver(serial=self.serial, profile=self.profile)
                self.rpa_emulator = AndroidRPADeviceEmulator(device_id=self.serial, real_execution=True)
            except Exception as e:
                print(f"Failed to init emulator components: {e}")

    async def health_check(self) -> bool:
        """Check if emulator and Instagram app are available"""
        if not HAS_EMULATOR:
            return False
        if not self.adb:
            return False
        try:
            # Check adb device
            result = self.adb.run(f"{self.adb.adb} devices")
            if self.serial not in result.get("stdout", ""):
                return False
            # Check if Instagram installed
            result = self.adb.run(f"{self.adb.adb} -s {self.serial} shell pm list packages | grep {self.package}")
            return self.package in result.get("stdout", "")
        except Exception:
            return False

    async def receive_messages(self, since: datetime | None = None) -> list[IncomingMessage]:
        """Получить новые сообщения из Instagram Direct через эмулятор"""
        if not self.messenger:
            raise RuntimeError("Emulator not initialized - check ADB and serial")
        
        try:
            # Open Direct inbox
            self.messenger.open_chats()
            # List chats
            threads = self.messenger.list_chats()
            messages = []
            for thread in threads[-10:]:  # last 10 chats
                chat_messages = self.messenger.read_chat(thread)
                for msg in chat_messages:
                    # Filter by since if provided
                    if since and msg.timestamp and msg.timestamp < since:
                        continue
                    messages.append(IncomingMessage(
                        message_id=msg.id if hasattr(msg, 'id') else f"ig_{thread.id}_{msg.timestamp}",
                        platform="instagram_emulator",
                        recipient_id=thread.id if hasattr(thread, 'id') else thread,
                        text=msg.text if hasattr(msg, 'text') else str(msg),
                        timestamp=msg.timestamp if hasattr(msg, 'timestamp') else datetime.now(timezone.utc)
                    ))
            return messages
        except Exception as e:
            raise RuntimeError(f"Failed to receive messages via emulator: {e}")

    async def send_message(self, recipient_id: str, text: str, metadata: dict | None = None) -> SentMessage:
        """Отправить сообщение в Instagram Direct через эмулятор (guarded outbox)"""
        if not self.messenger:
            raise RuntimeError("Emulator not initialized")
        
        try:
            # For emulator, recipient_id is thread id or username
            # Use guarded messenger: first add to outbox, then flush if confirmed
            auto_send = (metadata or {}).get("auto_send", False)
            
            if not auto_send:
                # Add to outbox queue (requires approval)
                result = self.messenger.send_reply(recipient_id, text, auto_send=False)
                return SentMessage(
                    message_id=f"ig_outbox_{int(datetime.now(timezone.utc).timestamp())}",
                    platform="instagram_emulator",
                    recipient_id=recipient_id,
                    text=text,
                    timestamp=datetime.now(timezone.utc),
                )
            else:
                # Direct send (with confirmation)
                result = self.messenger.send_reply(recipient_id, text, auto_send=True)
                # Flush outbox
                self.messenger.flush_outbox()
                
                return SentMessage(
                    message_id=f"ig_{int(datetime.now(timezone.utc).timestamp())}",
                    platform="instagram_emulator",
                    recipient_id=recipient_id,
                    text=text,
                    timestamp=datetime.now(timezone.utc),
                )
        except Exception as e:
            raise RuntimeError(f"Failed to send message via emulator: {e}")

    async def create_post(self, caption: str, image_path: str | None = None, metadata: dict | None = None) -> Dict[str, Any]:
        """Создать пост в Instagram через эмулятор"""
        if not HAS_EMULATOR:
            raise RuntimeError("Emulator dependencies missing")
        
        try:
            composer = PostComposer(adb=self.adb, storage=self.storage)
            # Compose post
            if image_path:
                result = composer.compose_with_image(caption, image_path)
            else:
                result = composer.compose_text_post(caption)
            
            return {
                "status": "created",
                "caption": caption,
                "image": image_path,
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            raise RuntimeError(f"Failed to create post via emulator: {e}")

    async def collect_feed(self, max_cards: int = 50, query: str | None = None) -> List[Dict[str, Any]]:
        """Собрать ленту Instagram через эмулятор"""
        if not self.adb:
            raise RuntimeError("ADB not initialized")
        
        try:
            # Use InstagramCollector or ReelsCollector
            from aios_core.platforms import get_platform
            platform = get_platform("instagram")
            
            collector = InstagramCollector(
                platform=platform,
                adb=self.adb,
                directory="platforms"
            )
            
            # Collect
            cards = collector.collect(max_cards=max_cards, query=query)
            
            # Convert to dicts
            return [
                {
                    "id": getattr(card, 'id', f"ig_{i}"),
                    "title": getattr(card, 'title', ''),
                    "author": getattr(card, 'author', ''),
                    "likes": getattr(card, 'likes', 0),
                    "image_url": getattr(card, 'image_url', ''),
                    "caption": getattr(card, 'caption', '') or getattr(card, 'title', ''),
                }
                for i, card in enumerate(cards[:max_cards])
            ]
        except Exception as e:
            # Fallback to RPA emulator
            if self.rpa_emulator:
                try:
                    result = self.rpa_emulator.execute_ui_action(
                        self.package,
                        "search",
                        {"query": query or "feed", "category": "all"}
                    )
                    return result.get("items", [])[:max_cards]
                except Exception as e2:
                    raise RuntimeError(f"Feed collection failed: {e}, fallback also failed: {e2}")
            raise RuntimeError(f"Failed to collect feed: {e}")

    async def collect_reels(self, max_cards: int = 50) -> List[Dict[str, Any]]:
        """Собрать Reels через эмулятор"""
        try:
            from aios_core.platforms import get_platform
            from aios_core.platforms.reelscout import ReelsCollector
            
            platform = get_platform("instagram")
            collector = ReelsCollector(
                platform=platform,
                adb=self.adb,
                directory="platforms"
            )
            
            cards = collector.collect(max_cards=max_cards)
            
            return [
                {
                    "id": getattr(card, 'id', f"reel_{i}"),
                    "title": getattr(card, 'title', ''),
                    "author": getattr(card, 'author', ''),
                    "video_url": getattr(card, 'video_url', ''),
                }
                for i, card in enumerate(cards[:max_cards])
            ]
        except Exception as e:
            raise RuntimeError(f"Failed to collect reels: {e}")

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        """Получить информацию о пользователе через эмулятор"""
        if not self.rpa_emulator:
            return {"user_id": user_id, "platform": "instagram_emulator"}
        
        try:
            result = self.rpa_emulator.execute_ui_action(
                self.package,
                "get_user_info",
                {"user_id": user_id}
            )
            return result
        except Exception as e:
            return {"user_id": user_id, "platform": "instagram_emulator", "error": str(e)}

    async def login(self, username: str = None, password: str = None) -> Dict[str, Any]:
        """Логин в Instagram через эмулятор с использованием env секретов"""
        if not self.login_driver:
            raise RuntimeError("Login driver not initialized")
        
        try:
            # Use secrets from env if not provided
            if not username:
                from aios_core.platforms.secrets import required_secret
                username = required_secret("instagram", "USERNAME", profile=self.profile)
            if not password:
                from aios_core.platforms.secrets import required_secret
                password = required_secret("instagram", "PASSWORD", profile=self.profile)
            
            result = self.login_driver.drive(self.package, query=None)
            
            return {
                "status": "logged_in",
                "username": username,
                "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            raise RuntimeError(f"Login failed: {e}")

    def get_storage(self):
        """Get storage instance"""
        return self.storage

# Keep old Graph API adapter for backward compatibility
# Now PlatformRegistry will have both instagram (Graph API) and instagram_emulator (ADB)
