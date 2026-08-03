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
from datetime import datetime, timezone
from typing import Any, Dict, List
from pathlib import Path

from .chrome_twin_adapter import ChromeTwinAdapter
from .base import IncomingMessage, SentMessage

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
            # количество объявлений: "Оголошення" + число рядом
            ads_count = None
            m = re.search(r"Оголошення\s*(\d+)", body, re.IGNORECASE)
            if m:
                ads_count = int(m.group(1))
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

    async def create_ad(self, title: str, description: str, price: str, category: str = "other", images: List[str] = None) -> Dict[str, Any]:
        """Создать объявление через Chrome Twin (актуальная форма /d/uk/adding/)."""
        page = await self._ensure_browser()
        try:
            await page.goto("https://www.olx.ua/d/uk/adding/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(6000)
            # Проверка: телефон подтверждён?
            body = await page.inner_text("body")
            if any(k in body.lower() for k in ("підтвердіть", "подтвердите", "код підтвердження",
                                               "отримати код", "підтвердити свій")):
                return {"status": "phone_not_confirmed",
                        "error": "Нужно подтвердить телефон OLX (через VNC, команда «подтверди телефон OLX»)"}

            # Заполнить заголовок
            for sel in ("input[name='title']", "input[placeholder*='назв']", "input[placeholder*='Название']",
                        "input[data-testid*='title']", "textarea[placeholder*='назв']"):
                try:
                    el = page.locator(sel).first
                    await el.wait_for(state="visible", timeout=5000)
                    await el.fill(title)
                    break
                except Exception:
                    continue

            # Описание
            for sel in ("textarea[name='description']", "textarea[placeholder*='опис']",
                        "textarea[placeholder*='Описание']", "[contenteditable='true'][data-qa*='desc']"):
                try:
                    el = page.locator(sel).first
                    await el.wait_for(state="visible", timeout=5000)
                    await el.fill(description)
                    break
                except Exception:
                    continue

            # Цена
            if price:
                for sel in ("input[name='price']", "input[placeholder*='цін']", "input[placeholder*='цен']",
                            "input[data-testid*='price']"):
                    try:
                        el = page.locator(sel).first
                        await el.wait_for(state="visible", timeout=4000)
                        await el.fill(str(price))
                        break
                    except Exception:
                        continue

            # Фото (если переданы)
            if images:
                try:
                    fi = page.locator("input[type='file']").first
                    if await fi.count():
                        await fi.set_input_files([im for im in images if os.path.exists(im)])
                        await page.wait_for_timeout(4000)
                except Exception:
                    pass

            await page.wait_for_timeout(2000)
            shot = f"/tmp/aios_acct_olx_add_{int(__import__('time').time())}.png"
            try:
                await page.screenshot(path=shot)
            except Exception:
                shot = None
            return {"status": "draft_created", "title": title, "description": description[:100],
                    "price": price, "screenshot": shot}
        except Exception as e:
            print(f"Create ad failed: {e}")
            return {"status": "failed", "error": str(e)}

# Alias for backward compat
OLXChromeTwin = OLXChromeTwinAdapter
