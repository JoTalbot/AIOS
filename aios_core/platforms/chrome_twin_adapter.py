"""
Chrome Twin Adapter — Двойник реального пользователя в Google Chrome
Браузер с подключенным личным Google аккаунтом, выполняет любые действия по команде

Функции:
- Запуск Chrome с пользовательским профилем (где залогинен Google аккаунт)
- Навигация, клики, ввод, скролл, ожидание элементов
- Google сервисы: Gmail, Drive, Docs, Sheets, Calendar, YouTube, Maps, Translate, etc.
- Любые сайты: автоматизация через Playwright/Selenium
- Natural language команды: "отправь письмо", "создай документ", "проверь календарь"
- Скриншоты и vision (browser_vision MCP)

Безопасность:
- Использует отдельный Chrome профиль (не основной)
- Профиль хранится в data/chrome_twin/<profile>/
- Никогда не сохраняет пароли в коде, только использует существующую сессию
- Все действия логируются в audit log

Требования:
- Chrome/Chromium установлен
- Playwright (pip install playwright && playwright install chromium)
- Пользователь один раз логинится вручную в Google аккаунт в этом профиле
"""
from __future__ import annotations

import os
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path

from .base import IncomingMessage, PlatformAdapter, SentMessage

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    async_playwright = None

try:
    from .chrome_twin_vision import ChromeTwinVision  # Optional vision module
    HAS_VISION = True
except ImportError:
    HAS_VISION = False


class ChromeTwinAdapter(PlatformAdapter):
    """
    Двойник пользователя в Chrome с личным Google аккаунтом
    Выполняет любые действия по команде во всех сервисах Google и не только
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config or {})
        self.profile = self.config.get("profile") or os.getenv("CHROME_TWIN_PROFILE") or "default"
        self.user_data_dir = self.config.get("user_data_dir") or os.getenv("CHROME_TWIN_DATA_DIR") or f"data/chrome_twin/{self.profile}"
        self.headless = self.config.get("headless", False)  # Для Google лучше headless=False чтобы видеть капчу
        self.slow_mo = self.config.get("slow_mo", 100)  # Замедление для стабильности
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._vision = None
        
        # Создать директорию профиля
        Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
        
        # История действий для аудита
        self.action_history: List[Dict] = []

    async def _ensure_browser(self):
        """Запустить браузер с профилем если не запущен"""
        if self._page and self._context and self._browser:
            return self._page
        
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright не установлен: pip install playwright && playwright install chromium")
        
        self._playwright = await async_playwright().start()
        
        # Запустить Chrome с пользовательским профилем
        # Используем persistent context чтобы сохранить Google сессию
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",  # Скрыть что это автоматизация
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-dev-shm-usage",
            ],
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Получить или создать страницу
        if len(self._context.pages) > 0:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()
        
        # Инициализировать vision если есть
        if HAS_VISION:
            try:
                self._vision = ChromeTwinVision(self._page)
            except Exception:
                pass
        
        return self._page

    async def _log_action(self, action: str, params: Dict, result: Any = None):
        """Логировать действие для аудита"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "params": params,
            "result": str(result)[:500] if result else None,
            "profile": self.profile
        }
        self.action_history.append(entry)
        # Сохранить в файл для аудита
        try:
            log_path = Path(f"data/chrome_twin/{self.profile}/actions.jsonl")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    async def health_check(self) -> bool:
        """Проверить что браузер работает"""
        try:
            page = await self._ensure_browser()
            await page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=10000)
            return True
        except Exception:
            return False

    async def navigate(self, url: str) -> Dict[str, Any]:
        """Перейти на URL"""
        page = await self._ensure_browser()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await self._log_action("navigate", {"url": url})
        return {"status": "ok", "url": url, "title": await page.title()}

    async def click(self, selector: str = None, text: str = None, x: int = None, y: int = None) -> Dict[str, Any]:
        """Кликнуть по элементу"""
        page = await self._ensure_browser()
        try:
            if x is not None and y is not None:
                await page.mouse.click(x, y)
                await self._log_action("click", {"x": x, "y": y})
                return {"status": "clicked", "x": x, "y": y}
            elif text:
                await page.get_by_text(text, exact=False).first.click(timeout=10000)
                await self._log_action("click", {"text": text})
                return {"status": "clicked", "text": text}
            elif selector:
                await page.locator(selector).first.click(timeout=10000)
                await self._log_action("click", {"selector": selector})
                return {"status": "clicked", "selector": selector}
            else:
                raise ValueError("Need selector, text, or x,y")
        except Exception as e:
            await self._log_action("click_failed", {"selector": selector, "text": text, "error": str(e)})
            raise RuntimeError(f"Click failed: {e}")

    async def type_text(self, selector: str = None, text: str = "", clear: bool = True, press_enter: bool = False) -> Dict[str, Any]:
        """Ввести текст в элемент"""
        page = await self._ensure_browser()
        try:
            locator = None
            if selector:
                locator = page.locator(selector).first
            else:
                # Try to find focused input or first input
                locator = page.locator("input:focus, textarea:focus, [contenteditable=true]").first
            
            if clear:
                await locator.press("Control+A")
                await locator.press("Backspace")
            
            await locator.fill(text)
            await self._log_action("type", {"selector": selector, "text": text[:100], "clear": clear})
            
            if press_enter:
                await locator.press("Enter")
            
            return {"status": "typed", "text": text[:100]}
        except Exception as e:
            await self._log_action("type_failed", {"selector": selector, "error": str(e)})
            raise RuntimeError(f"Type failed: {e}")

    async def execute_google_action(self, service: str, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Выполнить действие в Google сервисе"""
        params = params or {}
        service = service.lower()
        action = action.lower()
        
        # Карта Google сервисов и их URL
        google_urls = {
            "gmail": "https://mail.google.com/mail/u/0/#inbox",
            "drive": "https://drive.google.com/drive/my-drive",
            "docs": "https://docs.google.com/document/u/0/",
            "sheets": "https://docs.google.com/spreadsheets/u/0/",
            "slides": "https://docs.google.com/presentation/u/0/",
            "calendar": "https://calendar.google.com/calendar/u/0/r",
            "youtube": "https://www.youtube.com/",
            "maps": "https://www.google.com/maps",
            "translate": "https://translate.google.com/",
            "photos": "https://photos.google.com/",
            "contacts": "https://contacts.google.com/",
            "meet": "https://meet.google.com/",
            "keep": "https://keep.google.com/",
        }
        
        url = google_urls.get(service)
        if not url:
            raise ValueError(f"Unknown Google service: {service}. Available: {list(google_urls.keys())}")
        
        page = await self._ensure_browser()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await self._log_action("google_navigate", {"service": service, "url": url})
        
        # Выполнить действие в зависимости от сервиса
        if service == "gmail" and action == "send":
            # Отправить письмо
            to = params.get("to", "")
            subject = params.get("subject", "")
            body = params.get("body", "")
            
            # Кликнуть Compose
            await self.click(text="Compose", selector="div[role=button]:has-text('Compose')")
            await page.wait_for_timeout(2000)
            # Ввести To
            await self.type_text(selector="input[aria-label*='To'], input[name='to']", text=to)
            await page.wait_for_timeout(500)
            await page.keyboard.press("Tab")
            # Subject
            if subject:
                await self.type_text(selector="input[aria-label*='Subject'], input[name='subjectbox']", text=subject)
                await page.wait_for_timeout(500)
            # Body
            await self.type_text(selector="div[aria-label*='Message Body'], div[role='textbox']", text=body)
            # Send - Ctrl+Enter or click Send button
            if params.get("confirm", False):
                await self.click(text="Send", selector="div[role=button]:has-text('Send')")
                await self._log_action("gmail_send", {"to": to, "subject": subject})
                return {"status": "sent", "to": to, "subject": subject}
            else:
                return {"status": "drafted", "to": to, "subject": subject, "note": "Add confirm=True to actually send"}
        
        elif service == "calendar" and action == "create_event":
            title = params.get("title", "New Event")
            # Click Create button
            await self.click(text="Create", selector="button:has-text('Create')")
            await page.wait_for_timeout(1000)
            await self.type_text(selector="input[aria-label*='Title'], input[placeholder*='Title']", text=title)
            # More fields...
            return {"status": "event_draft", "title": title}
        
        elif service == "drive" and action == "upload":
            # Upload file logic via input type=file
            file_path = params.get("file_path", "")
            if file_path:
                # Click New -> File upload
                await self.click(text="New", selector="button:has-text('New')")
                # Handle file chooser
                # This is simplified - real implementation needs file chooser handling
                return {"status": "upload_initiated", "file": file_path}
        
        elif service == "docs" and action == "create":
            title = params.get("title", "Untitled")
            content = params.get("content", "")
            # Docs creation is via Drive -> New -> Google Docs, or direct URL
            await page.goto("https://docs.google.com/document/create", wait_until="networkidle")
            await page.wait_for_timeout(2000)
            # Type content
            if content:
                await self.type_text(selector="div[contenteditable=true]", text=content)
            return {"status": "doc_created", "title": title}
        
        # Generic: just navigate and return
        return {"status": "navigated", "service": service, "action": action, "url": page.url}

    async def execute_custom_action(self, instruction: str) -> Dict[str, Any]:
        """Выполнить произвольную инструкцию на естественном языке"""
        # This would ideally use LLM to parse instruction into actions
        # For now, implement simple keyword-based routing
        
        instruction_lower = instruction.lower()
        
        if "почту" in instruction_lower or "email" in instruction_lower or "gmail" in instruction_lower:
            # Extract to, subject, body via simple parsing or LLM
            # For demo, navigate to Gmail
            return await self.execute_google_action("gmail", "open", {})
        
        elif "календарь" in instruction_lower or "calendar" in instruction_lower:
            return await self.execute_google_action("calendar", "open", {})
        
        elif "документ" in instruction_lower or "docs" in instruction_lower:
            return await self.execute_google_action("docs", "open", {})
        
        elif "диск" in instruction_lower or "drive" in instruction_lower:
            return await self.execute_google_action("drive", "open", {})
        
        elif "ютуб" in instruction_lower or "youtube" in instruction_lower:
            return await self.execute_google_action("youtube", "open", {})
        
        else:
            # Generic: try to navigate to URL mentioned in instruction
            import re
            urls = re.findall(r'https?://\S+', instruction)
            if urls:
                return await self.navigate(urls[0])
            else:
                # Just return that we need more specific instruction
                return {"status": "need_clarification", "instruction": instruction, "suggestion": "Укажите конкретный сервис Google или URL"}

    async def screenshot(self, path: str = None) -> str:
        """Сделать скриншот"""
        page = await self._ensure_browser()
        if not path:
            path = f"/tmp/chrome_twin_screenshot_{int(datetime.now().timestamp())}.png"
        await page.screenshot(path=path, full_page=False)
        await self._log_action("screenshot", {"path": path})
        return path

    async def get_page_content(self) -> Dict[str, Any]:
        """Получить содержимое страницы + URL + title"""
        page = await self._ensure_browser()
        return {
            "url": page.url,
            "title": await page.title(),
            "content": await page.content()
        }

    async def close(self):
        """Закрыть браузер"""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    # PlatformAdapter interface compatibility
    async def receive_messages(self, since=None):
        # For Chrome Twin, messages are not from platform but from user commands
        # Return empty, actual commands come via execute_custom_action
        return []

    async def send_message(self, recipient_id: str, text: str, metadata=None):
        # For Chrome Twin, send_message could mean send email or chat message via Google Chat
        # We'll route to Gmail if recipient looks like email
        if "@" in recipient_id:
            return await self.execute_google_action("gmail", "send", {"to": recipient_id, "subject": metadata.get("subject") if metadata else "From Chrome Twin", "body": text, "confirm": metadata.get("confirm", False) if metadata else False})
        else:
            # Generic navigation
            return SentMessage(
                message_id=f"chrome_twin_{int(datetime.now(timezone.utc).timestamp())}",
                platform="chrome_twin",
                recipient_id=recipient_id,
                text=text,
                timestamp=datetime.now(timezone.utc)
            )

    async def mark_as_read(self, message_id: str) -> bool:
        return True

    async def get_user_info(self, user_id: str) -> dict:
        # Try to get Google account info from page
        page = await self._ensure_browser()
        try:
            await page.goto("https://myaccount.google.com/", wait_until="domcontentloaded", timeout=10000)
            # Try to extract email from page
            email_el = page.locator("div:has-text('@gmail.com')").first
            if await email_el.count() > 0:
                email = await email_el.text_content()
                return {"user_id": user_id, "platform": "chrome_twin", "email": email.strip()}
        except Exception:
            pass
        return {"user_id": user_id, "platform": "chrome_twin"}

# For backward compat with old registry that expects InstagramEmulator etc, we keep alias
ChromeTwin = ChromeTwinAdapter
