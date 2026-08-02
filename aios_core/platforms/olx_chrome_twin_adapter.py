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
            "headless": True,  # For server, but can be False for debugging
            "slow_mo": 200
        }
        default_config.update(config or {})
        super().__init__(config=default_config)
        
        self.olx_login = self.config.get("olx_login") or os.getenv("OLX_LOGIN") or "959052288"
        self.olx_url = "https://www.olx.ua/"
        self.is_logged_in = False

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
        """Создать объявление через эмулятор (требует логина)"""
        if not self.is_logged_in:
            await self.login_to_olx()
        
        page = await self._ensure_browser()
        try:
            # Navigate to new ad page
            await page.goto(f"{self.olx_url}adding/", wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(3000)
            
            # Fill title
            await page.fill("input[name='title'], input[placeholder*='назв'], input[placeholder*='Название']", title)
            await page.wait_for_timeout(500)
            
            # Fill description
            await page.fill("textarea[name='description'], textarea[placeholder*='опис'], textarea[placeholder*='Описание']", description)
            await page.wait_for_timeout(500)
            
            # Fill price
            if price:
                await page.fill("input[name='price'], input[placeholder*='цін'], input[placeholder*='цен']", price)
            
            # For images, would need file chooser handling - simplified
            # Real implementation would use page.set_input_files
            
            return {"status": "draft_created", "title": title, "description": description[:100], "price": price}
        except Exception as e:
            print(f"Create ad failed: {e}")
            return {"status": "failed", "error": str(e)}

# Alias for backward compat
OLXChromeTwin = OLXChromeTwinAdapter
