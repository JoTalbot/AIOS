"""
TikTok Chrome Twin Adapter — использует залогиненную сессию TikTok
в Chrome-профиле data/chrome_twin/default/ (вход выполнен вручную через VNC).

Функции (read-only):
- check_login — залогинен ли TikTok
- get_current_user — username (@...)
- get_profile_info — имя, подписчики, подписки, лайки, bio
- get_feed(limit) — последние видео из ленты (автор + описание)
- get_my_videos(limit) — видео из профиля

Архитектура:
- Наследует ChromeTwinAdapter (Playwright + persistent Chrome-профиль)
- Системный google-chrome-stable
- Сессия (cookies), без паролей в коде
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


class TiktokChromeTwinAdapter(ChromeTwinAdapter):
    """TikTok через Chrome Twin профиль с уже залогиненной сессией."""

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
        self.tt_url = "https://www.tiktok.com/"
        self.is_logged_in = False

    async def _ensure_browser(self):
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
        url = self.tt_url + path.lstrip("/")
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
            return "tiktok" in (title + page.url).lower()
        except Exception:
            return False

    async def check_login(self) -> Dict[str, Any]:
        page = await self._ensure_browser()
        await self._goto(page, "")
        await page.wait_for_timeout(3000)
        url = page.url
        user = await self.get_current_user(page)
        # TikTok без логина показывает «Войти»; с логином — аватар/профиль
        try:
            login_btn = await page.locator("a[href*='login'], [data-e2e*='login']").count()
        except Exception:
            login_btn = 0
        self.is_logged_in = user is not None or login_btn == 0
        return {"logged_in": self.is_logged_in, "username": user, "url": url}

    async def get_current_user(self, page=None) -> Optional[str]:
        """Username @... из ссылки на профиль в шапке/навбаре."""
        if page is None:
            page = await self._ensure_browser()
        # приоритет: nav-profile (аватар текущего пользователя), потом header/nav
        scopes = [
            "[data-e2e*='nav-profile'] a[href*='/@'], a[data-e2e*='nav-profile']",
            "header a[href*='/@'], nav a[href*='/@'], [data-e2e*='avatar'] a, a[data-e2e*='avatar']",
            "a[href*='/@']",
        ]
        for sel in scopes:
            try:
                links = await page.eval_on_selector_all(sel, "els => els.map(e => e.getAttribute('href'))")
                cand = []
                for href in links or []:
                    m = re.search(r"/@([a-zA-Z0-9_.]+)", href or "")
                    if m and m.group(1).lower() not in ("login", "signup", "terms", "privacy"):
                        cand.append(m.group(1))
                if cand:
                    return max(set(cand), key=cand.count)
            except Exception:
                continue
        return None

    async def get_profile_info(self) -> Dict[str, Any]:
        """Имя, подписчики, подписки, лайки, bio (из meta-тегов профиля)."""
        login = await self.check_login()
        username = login.get("username")
        if not username:
            return {"error": "not_logged_in", "logged_in": False}
        page = await self._ensure_browser()
        # заход на профиль с ретраем (TikTok иногда отдаёт ленту вместо профиля)
        for attempt in range(3):
            try:
                await page.goto(f"{self.tt_url}@{username}", wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(11000)
            except Exception:
                await page.wait_for_timeout(3000)
            body_check = ""
            try:
                body_check = await page.inner_text("body")
            except Exception:
                pass
            if f"@{username}" in body_check or username in (await page.title()):
                break
            await page.wait_for_timeout(3000)

        async def _meta(prop: str) -> str:
            try:
                val = await page.evaluate(
                    """(p) => {
                        const el = document.querySelector(`meta[property="${p}"]`)
                            || document.querySelector(`meta[name="${p}"]`);
                        return el ? el.content : null;
                    }""", prop)
                return val or ""
            except Exception:
                return ""

        desc = await _meta("og:description") or ""
        title = await _meta("og:title") or ""

        def _num(text: str, pattern: str) -> Optional[int]:
            m = re.search(pattern, text, re.IGNORECASE)
            if not m:
                return None
            t = m.group(1).strip().lower()
            mult = 1
            if "k" in t:
                mult = 1000
            elif "m" in t:
                mult = 1_000_000
            digits = re.sub(r"[^\d.,]", "", t.replace("k", "").replace("m", ""))
            digits = digits.replace(",", ".").strip(".")
            if not digits or digits == ".":
                return None
            try:
                return int(float(digits) * mult)
            except ValueError:
                return None

        # счётчики из meta (если есть) и из видимого текста профиля
        followers = _num(desc, r"([\d.,]+[kKmM]?)\s*(подписчик|підписник|слідкувач|followers)")
        following = _num(desc, r"([\d.,]+[kKmM]?)\s*(подписок|підписок|слідкує|following)")
        likes = _num(desc, r"([\d.,]+[kKmM]?)\s*(лайк|подоб|уподобань|уподобайк|likes)")

        # видимый текст профиля: числа рядом с лейблами счётчиков
        try:
            body_text = await page.inner_text("body")
        except Exception:
            body_text = ""
        if body_text:
            if followers is None:
                followers = _num(body_text, r"([\d.,]+[kKmM]?)\s*(Слідкувач|Подписчик|Підписник|Followers)")
            if following is None:
                following = _num(body_text, r"([\d.,]+[kKmM]?)\s*(Слідкування|Слідкує|Подписок|Підписок|Following)")
            if likes is None:
                likes = _num(body_text, r"([\d.,]+[kKmM]?)\s*(Уподобайк|Уподобань|Лайк|Likes)")
            # bio: первая неслужебная строка (не счётчик, не навигация)
            lines = [l.strip() for l in body_text.splitlines() if l.strip()]
            bio = ""
            for l in lines:
                if re.match(r"^[\d.,]+[kKmM]?$", l) or l in ("·", "•"):
                    continue
                low = l.lower()
                if any(k in low for k in ("слідкувач", "подписчик", "підписник", "following",
                                          "слідкує", "подписок", "followers", "уподобайк",
                                          "лайк", "likes", "відео", "видео", "video",
                                          "tiktok", "головна", "пошук", "search", "вхід",
                                          "войти", "log in", "увійти", "профіль", "профиль",
                                          "редагувати", "поділитися", "поделиться", "загрузить",
                                          "upload", "повідомлення", "inbox", "сповіщення",
                                          "settings", "налаштування", "творці", "авторы",
                                          "живі", "live", "популярні", "ігри", "друзі",
                                          "збережені", "рекомендовані", "для вас", "кнопка",
                                          "меню", "закрити", "скасувати", "відмінити", "завантаж",
                                          "для тебе", "див. інше", "слідкування", "друзі",
                                          "активність", "більше", "завантажити", "профіль",
                                          "міжнародний заголовок", "акаунти, за якими ти слідкуєш",
                                          "компанія", "програма", "умови й політики", "оновити",
                                          "зрозуміло", "вподобано", "останнє", "популярне",
                                          "найдавніші", "відео", "обране")):
                    continue
                if len(l) >= 2 and len(l) < 200:
                    bio = l
                    break
            if bio.lower() in ("немає біографії.", "нет биографии.", "no bio yet.", "немає біографії"):
                bio = ""
        else:
            bio = desc

        # имя из title: "(12)Jo Talbot565 (@jotalbotkubik) | TikTok"
        name = ""
        m_name = re.search(r"\)([^(]+?)\(@", title)
        if m_name:
            name = m_name.group(1).strip()
        if not name:
            m_name2 = re.search(r"\(([^()]{2,40})\)\s*\(@", title)
            if m_name2:
                name = m_name2.group(1).strip()
        if not name:
            name = title.split("(@")[0].strip()
        shot = f"/tmp/aios_acct_tt_{int(__import__('time').time())}.png"
        try:
            await page.screenshot(path=shot)
        except Exception:
            shot = None
        result = {
            "username": username,
            "name": name,
            "followers": followers,
            "following": following,
            "likes": likes,
            "bio": bio or None,
            "profile_url": f"{self.tt_url}@{username}",
            "screenshot": shot,
        }
        await self._log_action("tiktok_get_profile", {"username": username}, result)
        return result

    async def get_my_videos(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Видео из профиля (описания)."""
        login = await self.check_login()
        username = login.get("username")
        if not username:
            return [{"error": "not_logged_in"}]
        page = await self._ensure_browser()
        await self._goto(page, f"@{username}")
        await page.wait_for_timeout(4000)
        vids = []
        seen = set()
        try:
            items = await page.eval_on_selector_all(
                "div[data-e2e*='video'], a[href*='/video/']",
                """els => els.map(e => {
                    const t = (e.innerText || e.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 300);
                    return t;
                }).filter(t => t.length > 5)""")
            for t in items or []:
                if t in seen:
                    continue
                seen.add(t)
                vids.append({"text": t})
                if len(vids) >= limit:
                    break
        except Exception:
            pass
        return vids

    async def get_feed(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Посты ленты «Для вас» (автор + описание)."""
        page = await self._ensure_browser()
        await self._goto(page, "")
        await page.wait_for_timeout(4000)
        vids = []
        seen = set()
        try:
            items = await page.eval_on_selector_all(
                "div[data-e2e*='feed'], div[data-e2e*='video']",
                """els => els.map(e => {
                    const t = (e.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 300);
                    return t;
                }).filter(t => t.length > 10)""")
            for t in items or []:
                if t in seen:
                    continue
                seen.add(t)
                vids.append({"text": t})
                if len(vids) >= limit:
                    break
        except Exception:
            pass
        return vids
