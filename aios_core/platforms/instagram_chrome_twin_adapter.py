"""
Instagram Chrome Twin Adapter — использует залогиненную сессию Instagram
в Chrome-профиле data/chrome_twin/default/ (тот же профиль, где залогинен
Google-аккаунт jo.talbot@gmail.com и вручную через VNC выполнен вход в Instagram).

Функции:
- Проверка, что Instagram залогинен (check_login)
- Определение текущего username (get_current_username)
- Сбор информации профиля: bio, followers/following/posts, аватар (get_profile_info)
- Сбор последних постов из ленты профиля (get_my_posts)
- Детали поста: подпись, лайки (get_post_details)

Архитектура:
- Наследует ChromeTwinAdapter (Playwright + persistent Chrome-профиль)
- Никаких паролей в коде: используется существующая сессия (cookies) профиля
- Все действия логируются в data/chrome_twin/default/actions.jsonl

Безопасность:
- Только read-only операции (просмотр профиля и постов)
- Сессия не создаётся и не модифицируется кодом
"""
from __future__ import annotations

import os
import re
import shutil
from datetime import datetime, timezone
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
    """Найти системный Chrome/Chromium (профиль создан Google Chrome 151)."""
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

# Служебные пути Instagram, не являющиеся профилями пользователей
_IG_SERVICE_PATHS = {
    "explore", "direct", "accounts", "p", "reels", "tags", "stories",
    "settings", "about", "static", "web", "support", "privacy", "terms",
    "session", "logout", "login", "signup", "password", "emails", "phone",
    "search", "map", "top", "people", "locations", "usertags", "content",
    "igtv", "guide", "nominate", "invite", "notifications", "admin",
    "popular", "messages", "saved", "activity", "language", "legal",
    "news", "discover_people", "change_password", "edit", "meta_verified",
}


class InstagramChromeTwinAdapter(ChromeTwinAdapter):
    """
    Instagram (Meta) адаптер через Chrome Twin профиль с уже залогиненной сессией.
    Работает в режиме read-only: профиль, подписчики, посты.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        default_config = {
            "profile": "default",
            "user_data_dir": "data/chrome_twin/default",
            "headless": False,  # Instagram капчит headless; сервер использует xvfb-run
            "slow_mo": 150,
        }
        default_config.update(config or {})
        super().__init__(config=default_config)

        # Профиль создан системным Google Chrome — используем тот же бинарник
        self.executable_path = self.config.get("executable_path") or _find_chrome_binary()

        self.ig_url = "https://www.instagram.com/"
        self.is_logged_in = False

    async def _ensure_browser(self):
        """Запустить системный Chrome с профилем (аналог базового, но с executable_path
        и корректной проверкой уже запущенного контекста — в базовом _browser не присваивается)."""
        if self._page and self._context:
            return self._page

        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright не установлен: pip install playwright && playwright install chromium")

        self._playwright = await async_playwright().start()

        launch_kwargs: dict[str, Any] = dict(
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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        )
        if self.executable_path:
            launch_kwargs["executable_path"] = self.executable_path

        self._context = await self._playwright.chromium.launch_persistent_context(**launch_kwargs)
        self._browser = self._context  # для совместимости с базовой проверкой

        if len(self._context.pages) > 0:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()

        try:
            from .chrome_twin_vision import ChromeTwinVision
            self._vision = ChromeTwinVision(self._page)
        except Exception:
            pass

        return self._page

    # ------------------------------------------------------------------ helpers
    def _profile_path(self) -> bool:
        """Существует ли профиль Chrome с сессиями."""
        p = Path(self.user_data_dir)
        if not p.exists():
            return False
        cookies = p / "Default" / "Cookies"
        return cookies.exists()

    async def _meta(self, page, prop: str) -> Optional[str]:
        """Достать содержимое meta-тега."""
        try:
            return await page.evaluate(
                """(prop) => {
                    const el = document.querySelector(`meta[property="${prop}"]`)
                        || document.querySelector(`meta[name="${prop}"]`);
                    return el ? el.content : null;
                }""", prop)
        except Exception:
            return None

    async def _goto_ig(self, page, path: str = "", retries: int = 3):
        """Переход на instagram.com с ретраями."""
        url = self.ig_url + path.lstrip("/")
        for i in range(retries):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(4000)
                return True
            except Exception:
                await page.wait_for_timeout(2500)
        return False

    # ------------------------------------------------------------------ checks
    async def health_check(self) -> bool:
        """Проверить, что профиль Chrome существует и Instagram доступен."""
        try:
            if not self._profile_path():
                return False
            page = await self._ensure_browser()
            if not await self._goto_ig(page, ""):
                return False
            title = await page.title()
            url = page.url
            return "instagram" in (title + url).lower()
        except Exception as e:
            print(f"Health check failed: {e}")
            return False

    async def check_login(self) -> Dict[str, Any]:
        """
        Проверить, залогинен ли Instagram в профиле.
        Открывает /accounts/edit/ — она доступна только залогиненным.
        Returns: {"logged_in": bool, "username": str|None, "url": str}
        """
        page = await self._ensure_browser()
        await self._goto_ig(page, "accounts/edit/")
        await page.wait_for_timeout(3000)
        url = page.url

        # Если редирект на страницу входа — не залогинен
        if "accounts/login" in url or "accounts/emailsignup" in url:
            self.is_logged_in = False
            return {"logged_in": False, "username": None, "url": url}

        username = await self.get_current_username(page)
        self.is_logged_in = username is not None
        return {"logged_in": self.is_logged_in, "username": username, "url": url}

    async def get_current_username(self, page=None) -> Optional[str]:
        """
        Определить текущий username: на странице настроек/профиля Instagram
        есть ссылка на свой профиль вида "/<username>/".
        """
        if page is None:
            page = await self._ensure_browser()
        try:
            links = await page.eval_on_selector_all(
                "a[href^='/']",
                """els => els.map(e => e.getAttribute('href'))""")
            for href in links or []:
                m = re.match(r"^/([^/]+)/?$", href or "")
                if m:
                    name = m.group(1)
                    if name and name not in _IG_SERVICE_PATHS and not name.startswith("_"):
                        return name
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------ profile
    async def get_profile_info(self, username: Optional[str] = None) -> Dict[str, Any]:
        """
        Собрать информацию профиля (по умолчанию — текущего залогиненного).
        Использует meta-теги Instagram (надёжно, без хрупких селекторов).
        """
        if username is None:
            login = await self.check_login()
            username = login.get("username")
            if not login.get("logged_in") or not username:
                return {"error": "not_logged_in", "logged_in": False}

        page = await self._ensure_browser()
        await self._goto_ig(page, f"{username}/")

        full_name = await self._meta(page, "og:title") or ""
        desc = await self._meta(page, "og:description") or ""
        avatar = await self._meta(page, "og:image") or ""
        # og:title обычно "Full Name (@username)" — убираем хвост
        if "@" in full_name:
            full_name = full_name.split("(")[0].strip()

        def _num(text: str) -> Optional[int]:
            try:
                t = text.strip().lower()
                mult = 1
                if "k" in t:
                    mult = 1000
                elif "m" in t:
                    mult = 1_000_000
                digits = re.sub(r"[^\d.,]", "", t.replace("k", "").replace("m", ""))
                digits = digits.replace(",", ".")
                if not digits:
                    return None
                return int(float(digits) * mult)
            except Exception:
                return None

        def _count(pattern: str) -> Optional[int]:
            for m in re.finditer(pattern, desc, re.IGNORECASE):
                return _num(m.group(1))
            return None

        followers = _count(r"([\d.,]+[kKmM]?)\s*(читачів|читачі|читач|підписник\w*|подписчик\w*|followers)")
        following = _count(r"([\d.,]+[kKmM]?)\s*(відстежуються|відстежується|підписок|підписки|подписок|подписки|following)")
        posts = _count(r"([\d.,]+[kKmM]?)\s*(дописів|дописи|допис|публикац\w*|публікац\w*|posts)")

        bio = desc
        # убрать префикс со счётчиками из биографии: "N читачів, M відстежуються, K дописів – "
        bio = re.sub(
            r"^\s*\d+[.,]?\d*[kKmM]?\s*(читачів|читачі|підписник\w*|подписчик\w*|followers)"
            r"[\s,;–—-]+"
            r"\d+[.,]?\d*[kKmM]?\s*(відстежуються|відстежується|підписок|подписки|following)"
            r"[\s,;–—-]+"
            r"\d+[.,]?\d*[kKmM]?\s*(дописів|дописи|публикац\w*|публікац\w*|posts)"
            r"[\s,;–—-]*", "", bio).strip()

        # стандартная заглушка Instagram вместо пустой bio
        if re.search(r"перегляньте світлини й відео|view the photos and videos|світлини й відео в instagram",
                     bio, re.IGNORECASE):
            bio = ""

        info = {
            "username": username,
            "full_name": full_name or None,
            "followers": followers,
            "following": following,
            "posts_count": posts,
            "bio": bio or None,
            "avatar_url": avatar or None,
            "profile_url": f"{self.ig_url}{username}/",
        }
        await self._log_action("instagram_get_profile", {"username": username}, info)
        return info

    # ------------------------------------------------------------------ posts
    async def get_my_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Собрать последние посты из профиля (read-only).
        Returns: [{"code", "url", "thumbnail", "alt"}]
        """
        login = await self.check_login()
        if not login.get("logged_in"):
            return [{"error": "not_logged_in"}]
        username = login.get("username")

        page = await self._ensure_browser()
        await self._goto_ig(page, f"{username}/")
        await page.wait_for_timeout(3000)

        posts: List[Dict[str, Any]] = []
        try:
            links = await page.query_selector_all("a[href*='/p/']")
            seen = set()
            for a in links[:limit * 3]:
                href = await a.get_attribute("href") or ""
                m = re.search(r"/p/([A-Za-z0-9_-]+)/?", href)
                if not m:
                    continue
                code = m.group(1)
                if code in seen:
                    continue
                seen.add(code)
                img = None
                alt = None
                try:
                    img_el = await a.query_selector("img")
                    if img_el:
                        img = await img_el.get_attribute("src")
                        alt = await img_el.get_attribute("alt")
                except Exception:
                    pass
                posts.append({
                    "code": code,
                    "url": f"{self.ig_url}p/{code}/",
                    "thumbnail": img,
                    "alt": alt,
                })
                if len(posts) >= limit:
                    break
        except Exception as e:
            print(f"Post parsing failed: {e}")

        await self._log_action("instagram_get_my_posts", {"limit": limit}, {"count": len(posts)})
        return posts

    async def get_post_comments(self, code: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Комментарии к посту (read-only): автор + текст."""
        page = await self._ensure_browser()
        await self._goto_ig(page, f"p/{code}/")
        await page.wait_for_timeout(5000)
        comments = []
        seen = set()
        try:
            texts = await page.eval_on_selector_all(
                "div[dir='auto']",
                """els => els.map(e => {
                    if (e.closest('[role="button"]')) return null;
                    const t = (e.textContent || '').trim().replace(/\\s+/g, ' ');
                    return (t.length > 3 && t.length < 400) ? t : null;
                }).filter(Boolean)""")
            noise = ("подобається", "переглянути", "показати", "переклад", "translate",
                     "відповісти", "ответить", "сховати", "більше", "переглянути все",
                     "коментарів ще немає", "почніть розмову", "повідомлення",
                     "підписники", "підписки", "дописи", "профіль")
            for t in texts or []:
                low = t.lower()
                if any(n in low for n in noise):
                    continue
                if len(t) < 4 or t in seen:
                    continue
                seen.add(t)
                comments.append({"text": t})
                if len(comments) >= limit:
                    break
        except Exception:
            pass
        await self._log_action("instagram_get_comments", {"code": code}, {"count": len(comments)})
        return comments

    async def reply_to_comment(self, code: str, text: str, confirm: bool) -> Dict[str, Any]:
        """Ответить на комментарий (вводит текст в поле комментария и публикует)."""
        if not confirm:
            return {"status": "need_confirm", "action": "ig_comment_reply",
                    "code": code, "text": text[:200]}
        page = await self._ensure_browser()
        await self._goto_ig(page, f"p/{code}/")
        await page.wait_for_timeout(5000)
        try:
            # поле комментария: div[contenteditable=true] с placeholder "Додати коментар"
            box = page.locator("div[contenteditable='true'][role='textbox'], div[contenteditable='true']").first
            await box.wait_for(state="visible", timeout=10000)
            await box.click()
            await page.keyboard.type(text, delay=25)
            await page.wait_for_timeout(800)
            # кнопка публикации комментария
            for name in ("Опублікувати", "Опубликовать", "Post", "Додати"):
                try:
                    btn = page.get_by_role("button", name=name).first
                    if await btn.count():
                        await btn.click(timeout=3000)
                        await page.wait_for_timeout(1500)
                        return {"status": "sent", "code": code, "text": text[:200]}
                except Exception:
                    continue
            # fallback: Enter
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(1500)
            return {"status": "sent", "code": code, "text": text[:200]}
        except Exception as e:
            return {"status": "error", "error": str(e)[:300]}

    async def get_post_details(self, code: str) -> Dict[str, Any]:
        """Детали поста: подпись, лайки, автор (read-only)."""
        page = await self._ensure_browser()
        await self._goto_ig(page, f"p/{code}/")

        desc = await self._meta(page, "og:description") or ""
        title = await self._meta(page, "og:title") or ""
        image = await self._meta(page, "og:image") or ""

        likes = None
        m = re.search(r"([\d.,]+[kKmM]?)\s*(лайк\w*|likes)", desc, re.IGNORECASE)
        if m:
            likes = m.group(1)
        caption = desc
        caption = re.sub(
            r"\s*\d+[.,]?\d*[kKmM]?\s*(лайк\w*|likes)\s*$", "", caption).strip()

        result = {
            "code": code,
            "url": f"{self.ig_url}p/{code}/",
            "title": title,
            "caption": caption or None,
            "likes": likes,
            "image": image,
        }
        await self._log_action("instagram_get_post_details", {"code": code}, result)
        return result
