"""
Facebook Chrome Twin Adapter — использует залогиненную сессию Facebook
в Chrome-профиле data/chrome_twin/default/ (тот же профиль, где залогинен
Google-аккаунт jo.talbot@gmail.com; вход в Facebook выполнен вручную через VNC).

Функции (read-only):
- check_login — залогинен ли Facebook
- get_current_user — имя/username текущего аккаунта
- get_profile_info — имя, город, ссылка на профиль
- get_feed(limit) — последние посты из ленты (автор + текст)
- get_notifications_count — сколько уведомлений

Архитектура:
- Наследует ChromeTwinAdapter (Playwright + persistent Chrome-профиль)
- Использует системный google-chrome-stable (профиль создан им)
- Никаких паролей в коде: существующая сессия (cookies)
"""
from __future__ import annotations

import os
import re
import shutil
from typing import Any, Dict, List, Optional
from pathlib import Path

from .chrome_twin_adapter import ChromeTwinAdapter

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    async_playwright = None


def _find_chrome_binary() -> Optional[str]:
    candidates = [
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        shutil.which("google-chrome-stable"),
        shutil.which("google-chrome"),
        shutil.which("chromium-browser"),
        shutil.which("chromium"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


class FacebookChromeTwinAdapter(ChromeTwinAdapter):
    """Facebook (Meta) через Chrome Twin профиль с уже залогиненной сессией."""

    def __init__(self, config: dict[str, Any] | None = None):
        default_config = {
            "profile": "default",
            "user_data_dir": "data/chrome_twin/default",
            "headless": False,
            "slow_mo": 120,
        }
        default_config.update(config or {})
        super().__init__(config=default_config)
        self.executable_path = self.config.get("executable_path") or _find_chrome_binary()
        self.fb_url = "https://www.facebook.com/"
        self.is_logged_in = False

    async def _ensure_browser(self):
        """Запустить системный Chrome с профилем (корректная проверка контекста)."""
        if self._page and self._context:
            return self._page
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright не установлен")
        self._playwright = await async_playwright().start()
        kwargs: dict[str, Any] = dict(
            user_data_dir=str(Path(self.user_data_dir).resolve()),
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        )
        if self.executable_path:
            kwargs["executable_path"] = self.executable_path
        self._context = await self._playwright.chromium.launch_persistent_context(**kwargs)
        self._browser = self._context
        self._page = self._context.pages[0] if len(self._context.pages) > 0 else await self._context.new_page()
        try:
            from .chrome_twin_vision import ChromeTwinVision
            self._vision = ChromeTwinVision(self._page)
        except Exception:
            pass
        return self._page

    async def _goto(self, page, path: str = "", retries: int = 3):
        url = self.fb_url + path.lstrip("/")
        for i in range(retries):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(4000)
                return True
            except Exception:
                await page.wait_for_timeout(2500)
        return False

    async def health_check(self) -> bool:
        try:
            page = await self._ensure_browser()
            await self._goto(page, "")
            title = await page.title()
            return "facebook" in (title + page.url).lower() or "войти" not in page.url.lower()
        except Exception:
            return False

    async def check_login(self) -> Dict[str, Any]:
        """Проверить, залогинен ли Facebook."""
        page = await self._ensure_browser()
        await self._goto(page, "")
        await page.wait_for_timeout(3000)
        url = page.url
        # на страницу входа редиректит /login/
        if "login" in url.lower() or "checkpoint" in url.lower():
            self.is_logged_in = False
            return {"logged_in": False, "username": None, "url": url}
        user = await self.get_current_user(page)
        self.is_logged_in = user is not None
        return {"logged_in": self.is_logged_in, "username": user, "url": url}

    async def get_current_user(self, page=None) -> Optional[str]:
        """Имя текущего аккаунта (из ссылки на профиль /<username> в меню)."""
        if page is None:
            page = await self._ensure_browser()
        try:
            links = await page.eval_on_selector_all(
                "a[href*='facebook.com/'], a[href^='/']",
                "els => els.map(e => e.getAttribute('href'))")
            cand = []
            for href in links or []:
                href = href or ""
                # /username или /profile.php?id=
                m = re.search(r"facebook\.com/([a-zA-Z0-9.]+)/?$", href)
                if m and not any(x in m.group(1).lower() for x in
                                 ("login", "logout", "help", "settings", "pages",
                                  "groups", "events", "notifications", "messages",
                                  "friends", "watch", "marketplace", "profile.php")):
                    cand.append(m.group(1))
            if cand:
                # самый частый — профиль
                return max(set(cand), key=cand.count)
        except Exception:
            pass
        return None

    async def get_profile_info(self) -> Dict[str, Any]:
        """Имя, город, ссылка профиля (через профиль пользователя)."""
        login = await self.check_login()
        if not login.get("logged_in"):
            return {"error": "not_logged_in", "logged_in": False}
        username = login.get("username")
        page = await self._ensure_browser()
        await self._goto(page, "me" if not username else username)
        await page.wait_for_timeout(4000)
        title = await page.title()
        body = ""
        try:
            body = await page.inner_text("body")
        except Exception:
            pass
        lines = [l.strip() for l in body.splitlines() if l.strip()]
        # имя: строка перед "N — друзья"/"друзей"
        name = ""
        friends = None
        for i, l in enumerate(lines):
            m = re.search(r"(\d[\d\s]*)\s*[—-]\s*(друзья|друзей|friends)", l, re.IGNORECASE)
            if m:
                friends = int(re.sub(r"\D", "", m.group(1)))
                if i > 0 and lines[i - 1] and "фото" not in lines[i - 1].lower():
                    name = lines[i - 1]
                break
        if not name:
            # fallback: "Редактировать профиль" есть — имя обычно выше
            for i, l in enumerate(lines):
                if "редактировать профиль" in l.lower() and i > 0:
                    for j in range(i - 1, max(-1, i - 4), -1):
                        if lines[j] and len(lines[j]) > 1 and "друз" not in lines[j].lower():
                            name = lines[j]
                            break
                    break
        if not name:
            name = title.split(" - Facebook")[0].strip() if " - Facebook" in title else title.split(" | Facebook")[0].strip()
        # город
        city = None
        for l in lines:
            m = re.search(r"(?:место проживания|проживає|city|место жительства)[: ]*([\w\sА-Яа-яЁёІіЇїЄє'-]{2,40})", l, re.IGNORECASE)
            if m:
                city = m.group(1).strip()
                break
        # bio: строки после "Редактировать профиль" до "Ещё"/"Информация"
        bio_lines = []
        for i, l in enumerate(lines):
            if "редактировать профиль" in l.lower():
                for j in range(i + 1, min(i + 6, len(lines))):
                    nxt = lines[j]
                    if nxt.lower() in ("ещё", "все", "информация", "друзья", "фото", "reels", "личная информация"):
                        break
                    if len(nxt) >= 3 and not nxt.isdigit():
                        bio_lines.append(nxt)
                break
        bio = " | ".join(bio_lines)[:200] or None
        # скриншот
        shot = f"/tmp/aios_acct_fb_{int(__import__('time').time())}.png"
        try:
            await page.screenshot(path=shot)
        except Exception:
            shot = None
        result = {
            "name": name or username,
            "username": username,
            "friends": friends,
            "city": city,
            "bio": bio,
            "profile_url": f"{self.fb_url}{username or 'me'}",
            "screenshot": shot,
        }
        await self._log_action("facebook_get_profile", {}, result)
        return result

    async def get_feed(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Последние посты ленты (read-only): автор + текст."""
        page = await self._ensure_browser()
        await self._goto(page, "")
        await page.wait_for_timeout(4000)
        posts = []
        seen = set()
        try:
            # посты FB: div[role=article]
            items = await page.eval_on_selector_all(
                "div[role='article']",
                """els => els.map(e => {
                    const t = (e.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 500);
                    return t;
                }).filter(t => t.length > 20)""")
            for t in items or []:
                if t in seen:
                    continue
                seen.add(t)
                posts.append({"text": t})
                if len(posts) >= limit:
                    break
        except Exception:
            pass
        await self._log_action("facebook_get_feed", {"limit": limit}, {"count": len(posts)})
        return posts

    async def get_notifications_count(self) -> Optional[int]:
        """Число в бейдже уведомлений (svg с числом в навбаре)."""
        page = await self._ensure_browser()
        await self._goto(page, "")
        try:
            nums = await page.eval_on_selector_all(
                "[aria-label*='уведомлен'], [aria-label*='сповіщен'], [role='banner'] [role='button'] span",
                "els => els.map(e => e.textContent.trim()).filter(t => /^\\d+$/.test(t))")
            if nums:
                return max(int(n) for n in nums)
        except Exception:
            pass
        return None
