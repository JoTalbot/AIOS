"""
OLX Ukraine Chrome Twin Adapter — использует залогиненный Google аккаунт и сохраненные пароли из Chrome профиля
Логин для OLX: 959052288 (телефон)

Функции:
- Использует Chrome профиль data/chrome_twin/default/ где уже залогинен Google аккаунт jo.talbot@gmail.com
- В этом профиле сохранены пароли (включая для OLX)
- Заходит на olx.ua, логинится через Google или через телефон 959052288 + автозаполнение пароля из Chrome
- После логина может: собирать объявления, отправлять сообщения, создавать объявления, парсить цены

Архитектура:
- Наследует ChromeTwinAdapter для работы с браузером
- Использует Playwright с сохраненным профилем
- Для OLX: навигация, клики, ввод, автозаполнение паролей Chrome

Безопасность:
- Пароли не хардкодятся, используются из Chrome Password Manager (сохраненные)
- Логин 959052288 только для идентификации, пароль берется из сохраненных
- Все действия логируются в data/chrome_twin/default/actions.jsonl
"""
from __future__ import annotations

import os
import asyncio
import shutil
import re
import json
from datetime import datetime, timezone
from typing import Any, Dict, List
from pathlib import Path

from .chrome_twin_adapter import ChromeTwinAdapter, _try_cdp_attach
from .base import IncomingMessage, SentMessage

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
JOURNAL_PATH = _PROJECT_ROOT / "data" / "olx_published.json"


def _load_journal() -> list[dict]:
    """Журнал опубликованных объявлений (для «мои объявления»)."""
    try:
        if JOURNAL_PATH.exists():
            return json.loads(JOURNAL_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _journal_add(entry: dict) -> None:
    """Добавить запись в журнал публикаций (максимум 100)."""
    import json as _j
    try:
        JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        items = _load_journal()
        items.insert(0, entry)
        items = items[:100]
        JOURNAL_PATH.write_text(_j.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[olx-journal] add failed: {e}")


class OLXChromeTwinAdapter(ChromeTwinAdapter):
    """
    OLX Украина адаптер через Chrome Twin с залогиненным Google аккаунтом
    Использует сохраненные пароли из Chrome профиля для логина 959052288
    """

    def __init__(self, config: dict[str, Any] | None = None):
        # Use same profile as Chrome Twin where Google account is logged in
        default_config = {
            "profile": "default",
            "user_data_dir": "data/chrome_twin/default",
            "headless": False,  # сервер использует xvfb-run
            "slow_mo": 200
        }
        default_config.update(config or {})
        super().__init__(config=default_config)

        # Профиль создан системным Google Chrome — используем тот же бинарник
        self.executable_path = self.config.get("executable_path") or next(
            (c for c in ("/usr/bin/google-chrome-stable", "/usr/bin/google-chrome",
                         "/usr/bin/chromium-browser", "/usr/bin/chromium") if os.path.exists(c)),
            shutil.which("google-chrome-stable") or None)
        
        self.olx_login = self.config.get("olx_login") or os.getenv("OLX_LOGIN") or "959052288"
        self.olx_url = "https://www.olx.ua/"
        self.is_logged_in = False

    async def _ensure_browser(self):
        """Запустить системный Chrome с профилем (корректная проверка контекста)."""
        if self._page and self._context:
            return self._page
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError("Playwright не установлен")
        self._playwright = await async_playwright().start()
        # CDP: если уже запущен системный Chrome (aios-chrome-vnc) — работаем через него
        if self.cdp_url:
            _cdp_res = None
            for _att in range(4):
                _cdp_res = await _try_cdp_attach(self._playwright, self.cdp_url, "olx.ua")
                if _cdp_res is not None:
                    break
                await asyncio.sleep(2)
            if _cdp_res is not None:
                self._browser, self._context, self._page = _cdp_res
                return self._page
            raise RuntimeError(
                f"Chrome по CDP ({self.cdp_url}) недоступен: запустите systemctl start aios-chrome-vnc")


        kwargs = dict(
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
        return self._page

    async def account_info(self) -> dict:
        """Информация аккаунта OLX: имя и количество объявлений (read-only)."""
        page = await self._ensure_browser()
        try:
            await page.goto(f"{self.olx_url}uk/myaccount/", wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(5000)
            body = await page.inner_text("body")
            lines = [l.strip() for l in body.splitlines() if l.strip()]
            # имя — строка после первого "Ваш профіль" (это имя аккаунта)
            name = None
            for i, l in enumerate(lines):
                if "Ваш профіль" in l or "Ваш профиль" in l:
                    for j in range(i + 1, min(i + 4, len(lines))):
                        nxt = lines[j]
                        if nxt and "профіль" not in nxt.lower() and "профиль" not in nxt.lower() \
                                and len(nxt) < 60:
                            name = nxt
                            break
                    break
            # количество объявлений: «Активні (N)» в кабинете (главный счётчик)
            ads_count = None
            m = re.search(r"Активні\s*\((\d+)\)", body, re.IGNORECASE)
            if not m:
                m = re.search(r"Активні[^\d]{0,20}(\d+)", body, re.IGNORECASE)
            if m:
                ads_count = int(m.group(1))
            if ads_count is None:
                m3 = re.search(r"з (\d+) оголошень", body, re.IGNORECASE)
                if m3:
                    ads_count = int(m3.group(1))
            # баланс
            balance = None
            m2 = re.search(r"рахунок[^\d]*(\d[\d\s.,]*)\s*грн", body, re.IGNORECASE)
            if m2:
                balance = m2.group(1).strip()
            shot = f"/tmp/aios_acct_olx_{int(__import__('time').time())}.png"
            try:
                await page.screenshot(path=shot)
            except Exception:
                shot = None
            return {"status": "ok", "login": self.olx_login, "name": name,
                    "ads_count": ads_count, "balance": balance, "screenshot": shot}
        except Exception as e:
            return {"status": "error", "error": str(e)[:300]}

    async def health_check(self) -> bool:
        """Check if Chrome profile with Google account exists and OLX accessible"""
        try:
            # Check if Chrome profile exists
            profile_path = Path(self.user_data_dir)
            if not profile_path.exists():
                return False
            
            # Check if Cookies file exists (indicates profile was used)
            cookies_path = profile_path / "Default" / "Cookies"
            if not cookies_path.exists():
                return False
            
            # Try to navigate to OLX
            page = await self._ensure_browser()
            await page.goto(self.olx_url, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(2000)
            
            # Check if page loaded
            title = await page.title()
            return "OLX" in title or "olx" in page.url.lower()
        except Exception as e:
            print(f"Health check failed: {e}")
            return False

    async def login_to_olx(self, use_google: bool = True) -> Dict[str, Any]:
        """
        Логин в OLX Украина через:
        - Google аккаунт (если OLX поддерживает Login with Google и у тебя Google аккаунт с тем же email)
        - Или через телефон 959052288 + автозаполнение пароля из Chrome сохраненных паролей
        
        Args:
            use_google: If True, try Login with Google using logged-in Google account. If False, use phone + saved password.
        """
        page = await self._ensure_browser()
        
        try:
            print(f"Navigating to OLX login: {self.olx_url}")
            await page.goto(f"{self.olx_url}myaccount/", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Check if already logged in (look for profile icon, my account, etc.)
            content = await page.content()
            if "Мої оголошення" in content or "Мой профиль" in content or "Моє" in content or "Выйти" in content or "Вийти" in content:
                print("Already logged in to OLX (found My Ads/Profile)")
                self.is_logged_in = True
                await page.screenshot(path="/tmp/olx_already_logged.png")
                return {"status": "already_logged_in", "url": page.url, "login": self.olx_login}
            
            if use_google:
                # Try Login with Google button
                print("Trying Login with Google...")
                try:
                    # Look for Google login button
                    google_selectors = [
                        "button:has-text('Google')",
                        "button:has-text('Увійти через Google')",
                        "button:has-text('Войти через Google')",
                        "div[data-testid='google-login']",
                        "a:has-text('Google')",
                        "[aria-label*='Google']",
                    ]
                    
                    for sel in google_selectors:
                        try:
                            await page.wait_for_selector(sel, timeout=3000)
                            await page.click(sel)
                            print(f"Clicked Google login button with selector: {sel}")
                            await page.wait_for_timeout(5000)
                            
                            # After clicking Google login, it should use already logged-in Google account
                            # May need to select account
                            await page.screenshot(path="/tmp/olx_google_login_clicked.png")
                            
                            # Check if Google account chooser appears
                            try:
                                # Look for account with jo.talbot@gmail.com
                                await page.wait_for_selector(f"text=jo.talbot@gmail.com", timeout=5000)
                                await page.click(f"text=jo.talbot@gmail.com")
                                print("Selected jo.talbot@gmail.com account")
                                await page.wait_for_timeout(5000)
                            except Exception:
                                print("No account chooser, maybe auto-logged in or different flow")
                            
                            await page.screenshot(path="/tmp/olx_after_google_select.png")
                            print(f"After Google login attempt, URL: {page.url}")
                            
                            # Check if logged in now
                            content = await page.content()
                            if "Мої оголошення" in content or "Мой профиль" in content or "Вийти" in content or "Выйти" in content:
                                print("✅ Logged in to OLX via Google!")
                                self.is_logged_in = True
                                return {"status": "logged_in_via_google", "url": page.url, "login": self.olx_login}
                            
                            break
                        except Exception as e:
                            print(f"Google selector {sel} failed: {e}")
                            continue
                except Exception as e:
                    print(f"Google login attempt failed: {e}")
            
            # Fallback: Login via phone 959052288 + saved password autofill
            print(f"Trying login via phone {self.olx_login} with saved password from Chrome...")
            try:
                # Navigate to login page
                await page.goto(f"{self.olx_url}account/login/", wait_until="networkidle", timeout=20000)
                await page.wait_for_timeout(3000)
                await page.screenshot(path="/tmp/olx_login_page.png")
                
                # Find phone/email input and fill with 959052288
                phone_selectors = [
                    "input[type='tel']",
                    "input[name='phone']",
                    "input[placeholder*='телефон']",
                    "input[placeholder*='Phone']",
                    "input[type='text']",
                ]
                
                filled = False
                for sel in phone_selectors:
                    try:
                        await page.wait_for_selector(sel, timeout=3000)
                        # Check if input is visible and empty or contains phone
                        await page.fill(sel, self.olx_login)
                        print(f"Filled phone {self.olx_login} with selector {sel}")
                        filled = True
                        break
                    except Exception as e:
                        continue
                
                if not filled:
                    # Try typing via keyboard (field may be focused)
                    await page.keyboard.type(self.olx_login, delay=100)
                    print(f"Typed phone via keyboard: {self.olx_login}")
                
                await page.wait_for_timeout(1000)
                
                # Click Next or Continue
                try:
                    await page.get_by_role("button", name="Далі").click(timeout=3000)
                    print("Clicked Далі")
                except:
                    try:
                        await page.get_by_role("button", name="Next").click(timeout=3000)
                        print("Clicked Next")
                    except:
                        await page.keyboard.press("Enter")
                        print("Pressed Enter after phone")
                
                await page.wait_for_timeout(3000)
                await page.screenshot(path="/tmp/olx_after_phone.png")
                
                # Now password field should appear, Chrome should autofill from saved passwords
                # Wait for password input
                try:
                    await page.wait_for_selector("input[type='password']", timeout=10000)
                    print("Password field appeared, checking if Chrome autofilled...")
                    
                    # Check if password field has value (autofilled from saved passwords)
                    pwd_value = await page.eval_on_selector("input[type='password']", "el => el.value")
                    if pwd_value and len(pwd_value) > 0:
                        print(f"✅ Chrome autofilled password (length {len(pwd_value)}) from saved passwords!")
                    else:
                        print("Password not autofilled, trying to trigger autofill...")
                        # Click on password field to trigger autofill dropdown
                        await page.click("input[type='password']")
                        await page.wait_for_timeout(2000)
                        await page.screenshot(path="/tmp/olx_password_autofill.png")
                        # Try to select from autofill dropdown if appears
                        # For now, we'll try to proceed even without autofill
                    
                    # Click login button
                    try:
                        await page.get_by_role("button", name="Увійти").click(timeout=3000)
                        print("Clicked Увійти")
                    except:
                        try:
                            await page.get_by_role("button", name="Войти").click(timeout=3000)
                            print("Clicked Войти")
                        except:
                            await page.keyboard.press("Enter")
                            print("Pressed Enter for login")
                    
                    await page.wait_for_timeout(5000)
                    await page.screenshot(path="/tmp/olx_after_login.png")
                    print(f"After login, URL: {page.url}")
                    
                    content = await page.content()
                    if "Мої оголошення" in content or "Неправильний" not in content:
                        print("✅ Possibly logged in to OLX via phone + saved password!")
                        self.is_logged_in = True
                        return {"status": "logged_in_via_phone", "url": page.url, "login": self.olx_login}
                    else:
                        print("Login may have failed, checking content...")
                        if "Неправильний пароль" in content or "Невірний" in content:
                            print("❌ Wrong password")
                        await page.screenshot(path="/tmp/olx_login_failed.png")
                
                except Exception as e:
                    print(f"Password step failed: {e}")
                    await page.screenshot(path="/tmp/olx_no_password_field.png")
            
            except Exception as e:
                print(f"Phone login flow failed: {e}")
                import traceback
                traceback.print_exc()
                await page.screenshot(path="/tmp/olx_phone_login_failed.png")
            
            await page.screenshot(path="/tmp/olx_final.png")
            return {"status": "login_attempted", "url": page.url, "logged_in": self.is_logged_in}
            
        except Exception as e:
            print(f"OLX login failed: {e}")
            import traceback
            traceback.print_exc()
            try:
                await page.screenshot(path="/tmp/olx_error.png")
            except:
                pass
            return {"status": "failed", "error": str(e), "url": page.url if 'page' in locals() else "unknown"}

    async def collect_my_ads(self) -> list[Dict[str, Any]]:
        """Собрать мои объявления после логина"""
        if not self.is_logged_in:
            await self.login_to_olx()
        
        page = await self._ensure_browser()
        try:
            await page.goto(f"{self.olx_url}myaccount/announcements/", wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(3000)
            
            # Parse ads - look for ad cards
            # This is simplified, real parsing would use hints
            content = await page.content()
            
            # Try to extract ad titles via selectors
            ads = []
            try:
                # OLX my ads have specific structure
                elements = await page.query_selector_all("[data-testid='ad-card'], .css-1sw7q4x, [data-cy='ad-card']")
                for i, el in enumerate(elements[:20]):
                    try:
                        title = await el.text_content()
                        ads.append({"id": f"ad_{i}", "title": title[:100] if title else "No title"})
                    except:
                        continue
            except Exception as e:
                print(f"Ad parsing failed: {e}")
            
            return ads
        except Exception as e:
            print(f"Collect my ads failed: {e}")
            return []

    async def find_my_ads_by_search(self, titles: list[str], limit: int = 20) -> List[Dict[str, Any]]:
        """Найти свои объявления через поиск на сайте (по названию) и проверить владение."""
        import urllib.parse as _up
        page = await self._ensure_browser()
        ads = []
        for title in titles[:limit]:
            try:
                q = _up.quote(title)
                await page.goto(f"https://www.olx.ua/uk/search/?q={q}",
                                wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(5000)
                links = await page.eval_on_selector_all(
                    "a[href*='obyavlenie']", "els => els.map(e=>e.getAttribute('href'))")
                for l in links or []:
                    m = __import__('re').search(r"ID([A-Za-z0-9]+)", l or "")
                    slug = (l or "").split("/")[-1]
                    if m and title.lower().split() and any(w.lower() in slug.lower() for w in title.lower().split()[:3]):
                        ads.append({"id": m.group(1), "url": l, "title": title})
                        break
            except Exception:
                continue
        await self._log_action("olx_find_ads", {"titles": titles}, {"count": len(ads)})
        return ads

    async def list_my_ads(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Список моих объявлений: перебираем известные id (из публикаций) + пробуем кабинет."""
        page = await self._ensure_browser()
        await self._route_olx_fm(page)
        # известные id объявлений из истории публикаций
        ads = []
        try:
            published = _load_journal()
            for p in published[:limit]:
                ads.append({"id": p.get("ad_id") or p.get("short_id") or "?",
                            "title": p.get("title", ""),
                            "price": p.get("price", ""),
                            "published_at": p.get("ts", ""),
                            "url": p.get("url", "")})
        except Exception:
            pass
        # кабинет: карточки объявлений на /uk/myaccount/
        try:
            await page.goto("https://www.olx.ua/uk/myaccount/",
                            wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(5000)
            # таб «Ваші оголошення» (без клика список часто не рендерится)
            try:
                tab = page.get_by_text("Ваші оголошення").first
                if await tab.count():
                    await tab.click(timeout=4000)
                    await page.wait_for_timeout(5000)
            except Exception:
                pass
            body = await page.inner_text("body")
            if "Сторінку не знайдено" not in body:
                lines = body.splitlines()
                for i, ln in enumerate(lines):
                    mm = __import__('re').match(r"ID:\s*(\d{6,12})", (ln or "").strip())
                    if not mm:
                        continue
                    ad_id = mm.group(1)
                    if ad_id in [x.get("id") for x in ads]:
                        continue
                    price = ""
                    title = ""
                    for j in range(i - 1, max(0, i - 22) - 1, -1):
                        mp = __import__('re').match(r"^([\d][\d\s]{1,10})\s*грн\.?$", (lines[j] or "").strip())
                        if mp:
                            price = mp.group(1).replace(" ", "")
                            if j > 0:
                                title = (lines[j - 1] or "").strip()
                            break
                    ads.append({"id": ad_id, "title": title, "price": price, "url": ""})
                    if len(ads) >= limit + 1:
                        break
        except Exception:
            pass
        await self._log_action("olx_list_my_ads", {}, {"count": len(ads)})
        return ads

    async def delete_ad(self, ad_id: str, confirm: bool) -> Dict[str, Any]:
        """Удалить объявление по id (страница редактирования -> кнопка Видалити)."""
        if not confirm:
            return {"status": "need_confirm", "action": "olx_delete", "ad_id": ad_id}
        page = await self._ensure_browser()
        await self._route_olx_fm(page)
        try:
            await page.goto(f"https://www.olx.ua/d/uk/adding/edit/{ad_id}/", wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(8000)
            body = await page.inner_text("body")
            if any(k in body.lower() for k in ("не знайдено", "недоступн", "not found")):
                return {"status": "error", "error": f"Объявление {ad_id} не найдено"}
            # закрыть модалки
            for name in ("Ні, почати заново", "Закрити"):
                try:
                    b = page.get_by_role("button", name=name).first
                    if await b.count():
                        await b.click(timeout=3000)
                        await page.wait_for_timeout(1500)
                except Exception:
                    pass
            # кнопка «Видалити»
            clicked = False
            for sel in ("text=Видалити", "button:has-text('Видалити')", "text=Delete",
                        "[data-testid*='delete']", "text=Видалити оголошення"):
                try:
                    el = page.locator(sel).first
                    if await el.count():
                        await el.click(force=True, timeout=4000)
                        await page.wait_for_timeout(2500)
                        clicked = True
                        break
                except Exception:
                    continue
            if not clicked:
                # в новой версии OLX веб-кнопки «Видалити» может не быть —
                # пробуем деактивировать объявление в кабинете
                try:
                    await page.goto("https://www.olx.ua/uk/myaccount/",
                                    wait_until="domcontentloaded", timeout=25000)
                    await page.wait_for_timeout(5000)
                    try:
                        tab = page.get_by_text("Ваші оголошення").first
                        if await tab.count():
                            await tab.click(timeout=4000)
                            await page.wait_for_timeout(5000)
                    except Exception:
                        pass
                    # ждём карточку
                    found_card = False
                    for _w in range(15):
                        b3 = await page.inner_text("body")
                        if f"ID: {ad_id}" in b3:
                            found_card = True
                            break
                        await page.wait_for_timeout(1500)
                    if found_card:
                        # карточка = элемент с нашим ID, ищем в ней «Деактивувати»
                        deact = page.locator(
                            f"text=ID: {ad_id}").locator("xpath=ancestor::*[contains(@class,'listing') or contains(@class,'card') or contains(@class,'item')][1]")
                        try:
                            bt = page.get_by_role("button", name="Деактивувати").first
                            if await bt.count():
                                await bt.click(timeout=4000)
                                await page.wait_for_timeout(2000)
                                await page.screenshot(path="/tmp/olx_deactivated.png")
                                return {"status": "deactivated", "ad_id": ad_id,
                                        "note": "Кнопка «Видалити» в новой версии OLX недоступна — объявление деактивировано (скрыто из поиска)"}
                        except Exception:
                            pass
                except Exception:
                    pass
                await page.screenshot(path="/tmp/olx_delete_no_btn.png")
                return {"status": "error",
                        "error": "Кнопка «Видалити» не найдена (в новой версии OLX удаление возможно только из приложения)"}
            # подтверждение
            for name in ("Так, видалити", "Видалити", "Підтвердити", "OK", "Так"):
                try:
                    b = page.get_by_role("button", name=name).first
                    if await b.count():
                        await b.click(timeout=3000)
                        await page.wait_for_timeout(2500)
                        break
                except Exception:
                    continue
            await page.wait_for_timeout(2000)
            await page.screenshot(path="/tmp/olx_deleted.png")
            return {"status": "deleted", "ad_id": ad_id}
        except Exception as e:
            return {"status": "error", "error": str(e)[:300]}

    async def edit_ad(self, ad_id: str, title: str = "", description: str = "", price: str = "",
                      confirm: bool = False) -> Dict[str, Any]:
        """Редактировать объявление (страница /d/uk/adding/edit/ID/)."""
        page = await self._ensure_browser()
        await self._route_olx_fm(page)
        try:
            await page.goto(f"https://www.olx.ua/d/uk/adding/edit/{ad_id}/", wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(9000)
            body = await page.inner_text("body")
            if any(k in body.lower() for k in ("не знайдено", "недоступн")):
                return {"status": "error", "error": f"Объявление {ad_id} не найдено"}
            for name in ("Ні, почати заново", "Закрити"):
                try:
                    b = page.get_by_role("button", name=name).first
                    if await b.count():
                        await b.click(timeout=3000)
                        await page.wait_for_timeout(1500)
                except Exception:
                    pass
            if not confirm:
                await page.screenshot(path="/tmp/olx_edit_preview.png")
                return {"status": "need_confirm", "action": "olx_edit", "ad_id": ad_id,
                        "title": title, "description": description, "price": price,
                        "screenshot": "/tmp/olx_edit_preview.png"}
            # Заполнить поля (если заданы)
            if title:
                try:
                    ti = page.locator("input[placeholder*='напр.']").first
                    if await ti.count():
                        await ti.fill(title[:150])
                except Exception:
                    pass
            if description:
                try:
                    d = page.locator("textarea[placeholder*='Подумайте']").first
                    if await d.count():
                        await d.fill(description)
                except Exception:
                    pass
            if price:
                try:
                    p = page.locator("input#parameters.price.price, input[name='parameters.price.price']").first
                    if not (await p.count()):
                        p = page.locator("input[placeholder*='цін'], input[placeholder*='цен']").first
                    if await p.count():
                        await p.fill(str(price))
                except Exception:
                    pass
            await page.wait_for_timeout(1000)
            # Сохранить (новая форма: «Змінити оголошення»)
            for name in ("Змінити оголошення", "Зберегти", "Сохранить", "Опублікувати"):
                try:
                    b = page.get_by_role("button", name=name).first
                    if await b.count():
                        await b.click(timeout=4000)
                        await page.wait_for_timeout(4000)
                        break
                except Exception:
                    continue
            await page.screenshot(path="/tmp/olx_edited.png")
            return {"status": "edited", "ad_id": ad_id, "title": title, "price": price}
        except Exception as e:
            return {"status": "error", "error": str(e)[:300]}

    async def _route_olx_fm(self, page):
        """Перенаправляет olx.pl/fm/* -> olx.ua/fm/* (обход 403/ORB для датацентровых IP)."""
        async def _handler(route):
            url = route.request.url
            if "olx.pl/fm/" in url:
                new_url = url.replace("https://www.olx.pl/fm/", "https://www.olx.ua/fm/")
                try:
                    resp = await self._context.request.get(
                        new_url, headers={"User-Agent": "Mozilla/5.0"})
                    body = await resp.body()
                    ct = resp.headers.get("content-type", "application/javascript")
                    await route.fulfill(status=resp.status, headers={
                        "content-type": ct, "access-control-allow-origin": "*"}, body=body)
                    return
                except Exception:
                    pass
            await route.continue_()
        await page.route("**/fm/**", _handler)

    async def _goto_retry(self, page, url: str, times: int = 3, delay: int = 15) -> bool:
        """Перейти на страницу с ретраями (OLX-чат блокируется CloudFront флапами)."""
        for _i in range(times):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(5000)
                body = await page.inner_text("body")
                if "Request blocked" not in body and "403 ERROR" not in body:
                    return True
            except Exception:
                pass
            if _i < times - 1:
                await asyncio.sleep(delay)
        return False

    async def chat_list(self, limit: int = 20) -> Dict[str, Any]:
        """Список переписок OLX-чата (/uk/myaccount/answers)."""
        page = await self._ensure_browser()
        await self._route_olx_fm(page)
        if not await self._goto_retry(page, "https://www.olx.ua/uk/myaccount/answers"):
            return {"status": "error",
                    "error": "OLX-чат недоступен (CloudFront блокирует датацентровый IP). Попробуйте позже."}
        body = await page.inner_text("body")
        unread = "Непрочитані" in body or "НЕПРОЧИТАНІ" in body.upper()
        items = await page.eval_on_selector_all(
            "[data-testid='list-item-user-name']",
            """(els, limit) => els.slice(0, limit).map(p => {
                let c = p.parentElement;
                for (let i = 0; i < 5 && c; i++) { if ((c.children || []).length > 2) break; c = c.parentElement; }
                const name = p.textContent.trim();
                let text = '';
                const t = c ? c.querySelector('[data-testid="list-item-message-text"]') : null;
                if (t) text = t.textContent.trim();
                return {name, text};
            })""",
            limit)
        return {"status": "ok", "threads": items, "unread_present": unread, "count": len(items)}

    async def chat_read(self, contact: str, limit: int = 15) -> Dict[str, Any]:
        """Открыть переписку с контактом и вернуть сообщения."""
        page = await self._ensure_browser()
        await self._route_olx_fm(page)
        if not await self._goto_retry(page, "https://www.olx.ua/uk/myaccount/answers"):
            return {"status": "error", "error": "OLX-чат недоступен (CloudFront). Попробуйте позже."}
        try:
            await page.locator(
                f"[data-testid='list-item-user-name']:has-text('{contact}')").first.click(timeout=8000)
            await page.wait_for_timeout(5000)
        except Exception:
            return {"status": "error", "error": f"Переписка «{contact}» не найдена"}
        msgs = await page.eval_on_selector_all(
            "[data-testid='message']",
            """(els, limit) => els.slice(-limit).map(e => {
                const p = e.parentElement;
                const pcls = p ? (p.className || '') : '';
                // В OLX вёрстке: наши (sent) сообщения имеют один parent-класс,
                // сообщения клиента — другой (проверено вживую: sent css-1s1hr5l,
                // recv css-1wisyfd). Определяем mine по parent-классу.
                const sent = /1s1hr5l|sent|my-message|outgoing/i.test(pcls);
                const recv = /1wisyfd|recv|received|incoming/i.test(pcls) || !sent;
                return {text: (e.textContent || '').trim(), mine: sent, theirs: recv};
            })""",
            limit)
        return {"status": "ok", "contact": contact, "messages": msgs[-limit:][::-1]}

    async def chat_reply(self, contact: str, text: str) -> Dict[str, Any]:
        """Ответить в переписку OLX-чата (с ретраями и устойчивым поиском контакта)."""
        page = await self._ensure_browser()
        await self._route_olx_fm(page)
        if not await self._goto_retry(page, "https://www.olx.ua/uk/myaccount/answers"):
            return {"status": "error", "error": "OLX-чат недоступен (CloudFront). Попробуйте позже."}

        # ждём появления списка переписок (до 15с), т.к. JS-вёрстка грузится медленно
        clicked = False
        for _ in range(6):
            await page.wait_for_timeout(2500)
            try:
                item = page.locator(
                    f"[data-testid='list-item-user-name']:has-text('{contact}')").first
                if await item.count():
                    await item.click(timeout=5000)
                    clicked = True
                    break
            except Exception:
                continue
        if not clicked:
            return {"status": "error", "error": f"Переписка «{contact}» не найдена"}
        await page.wait_for_timeout(6000)

        filled = False
        for sel in ("textarea[placeholder*='Напишіть']", "textarea[placeholder*='Напишите']", "textarea"):
            try:
                box = page.locator(sel).first
                if await box.count() and await box.is_visible():
                    await box.click(timeout=3000)
                    await box.fill(text)
                    filled = True
                    break
            except Exception:
                continue
        if not filled:
            return {"status": "error", "error": "Поле ввода не найдено"}
        await page.wait_for_timeout(800)
        sent = False
        for sel in ("button[aria-label='Submit message']", "button[aria-label*='Надіслати']",
                    "[data-testid*='send']"):
            try:
                b = page.locator(sel).first
                if await b.count():
                    await b.click(timeout=3000)
                    sent = True
                    break
            except Exception:
                continue
        if not sent:
            try:
                await page.keyboard.press("Enter")
                sent = True
            except Exception:
                pass
        await page.wait_for_timeout(1500)
        return ({"status": "sent", "to": contact, "text": text[:200]} if sent else
                {"status": "error", "error": "Кнопка отправки не найдена"})

    async def create_ad(self, title: str, description: str, price: str, category: str = "other", images: List[str] = None, publish: bool = False) -> Dict[str, Any]:
        """Создать объявление через Chrome Twin (пошаговая форма /uk/adding/)."""
        page = await self._ensure_browser()
        try:
            await self._route_olx_fm(page)
            await page.goto("https://www.olx.ua/uk/adding/", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(8000)
            body = await page.inner_text("body")
            if any(k in body.lower() for k in ("підтвердіть", "подтвердите", "код підтвердження",
                                               "отримати код", "підтвердити свій")):
                return {"status": "phone_not_confirmed",
                        "error": "Нужно подтвердить телефон OLX (через VNC, команда «подтверди телефон OLX»)"}
            # закрыть модалку черновика
            try:
                btn = page.get_by_role("button", name="Ні, почати заново").first
                if await btn.count():
                    await btn.click(timeout=4000)
                    await page.wait_for_timeout(4000)
            except Exception:
                pass
            # Шаг 1: заголовок + Продовжити (OLX требует минимум 16 символов)
            title_final = (title or "").strip()[:150]
            if len(title_final) < 16:
                title_final = (title_final + " — б/у з авторазборки")[:150]
            ti = page.locator("input[placeholder*='напр.']").first
            await ti.fill(title_final)
            await page.wait_for_timeout(800)
            try:
                btn = page.get_by_role("button", name="Продовжити").first
                await btn.click(timeout=5000)
            except Exception:
                pass
            # ждём продвижения формы (появляется «Ціна»)
            for _w in range(12):
                try:
                    b2 = await page.inner_text("body")
                    if "Ціна" in b2 or "Цена" in b2 or "Опублікувати" in b2:
                        break
                except Exception:
                    pass
                await page.wait_for_timeout(1500)

            # Шаг 2: тип (Продати/Обмін), статус (Приватна особа), состояние (Вживане)
            for name in ("Продати", "Приватна особа", "Вживане"):
                try:
                    btn = page.get_by_role("button", name=name).first
                    if await btn.count():
                        await btn.click(timeout=3000)
                        await page.wait_for_timeout(600)
                except Exception:
                    pass

            # Шаг 3: категория — OLX сама предлагает её по заголовку («Наша пропозиція»).
            # Старой модалки с «Обрати» больше нет: поле «Обрати» — это валюта.
            try:
                sugg = page.locator("text=Наша пропозиція").first
                if await sugg.count():
                    await page.wait_for_timeout(2500)
            except Exception:
                pass

            # Описание
            try:
                desc = page.locator("textarea[placeholder*='Подумайте']").first
                if await desc.count():
                    await desc.fill(description)
            except Exception:
                pass

            # Цена (новая форма: input#parameters.price.price)
            if price:
                try:
                    p_el = page.locator("input#parameters.price.price, input[name='parameters.price.price']").first
                    if not (await p_el.count()):
                        p_el = page.locator("input[placeholder*='цін'], input[placeholder*='цен'], input[name='price']").first
                    if await p_el.count():
                        await p_el.fill(str(price))
                        await page.wait_for_timeout(600)
                except Exception:
                    pass

            # Фото (если переданы)
            if images:
                try:
                    fi = page.locator("input[type='file']").first
                    if await fi.count():
                        await fi.set_input_files([im for im in images if os.path.exists(im)])
                        await page.wait_for_timeout(4000)
                except Exception:
                    pass

            # публикация (если подтверждено)
            if publish:
                try:
                    btn = page.get_by_role("button", name="Опублікувати").first
                    if await btn.count():
                        await btn.click(timeout=5000)
                        await page.wait_for_timeout(10000)
                        shot = f"/tmp/aios_acct_olx_pub_{int(__import__('time').time())}.png"
                        try:
                            await page.screenshot(path=shot)
                        except Exception:
                            shot = None
                        # извлечь id объявления из URL/страницы
                        final_url = page.url or ""
                        short_id = ""
                        m_short = re.search(r"-ID([A-Za-z0-9]+)\.html", final_url)
                        if m_short:
                            short_id = m_short.group(1)
                        numeric_id = ""
                        try:
                            body_txt = await page.inner_text("body")
                            m_num = re.search(
                                r"(?:editing|statistics|promote)/(\d{6,12})"
                                r"|(?:ad-id|ad_id)[=/](\d{6,12})"
                                r"|(?:id[=/])(\d{6,12})",
                                final_url + " " + body_txt)
                            if m_num:
                                numeric_id = m_num.group(1) or m_num.group(2) or m_num.group(3)
                        except Exception:
                            pass
                        ad_id = numeric_id or short_id or ""
                        _journal_add({
                            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "ad_id": ad_id,
                            "short_id": short_id,
                            "url": final_url,
                            "title": title,
                            "price": price,
                        })
                        return {"status": "published", "title": title_final, "price": price,
                                "ad_id": ad_id, "url": final_url,
                                "screenshot": shot}
                except Exception:
                    pass
            shot = f"/tmp/aios_acct_olx_add_{int(__import__('time').time())}.png"
            try:
                await page.screenshot(path=shot)
            except Exception:
                shot = None
            return {"status": "draft_created", "title": title_final, "description": description[:100],
                    "price": price, "screenshot": shot}
        except Exception as e:
            print(f"Create ad failed: {e}")
            return {"status": "failed", "error": str(e)}

# Alias for backward compat
OLXChromeTwin = OLXChromeTwinAdapter
