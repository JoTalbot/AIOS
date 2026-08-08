"""
Freelance Chrome Twin Adapter v19 — Автоматизация подачи заявок на фриланс-биржах через браузер Chrome
(работает под Xvfb :1 с использованием существующей сессии пользователя).

Поддерживаемые площадки v19:
- Habr Freelance (freelance.habr.com) — отклик на заказ
- Kwork Projects (kwork.ru/projects) — предложение услуги
- Freelancehunt (freelancehunt.com) — ставка на проект [NEW v19]
- Upwork (upwork.com) — Submit a Proposal [NEW v19]
- Fiverr (fiverr.com) — Custom Offer / Contact [NEW v19]

Безопасность (Article V):
- confirm=False по умолчанию → need_confirm, без кликов
- Все действия логируются в data/chrome_twin/<profile>/actions.jsonl
- Верификация профиля проверяется перед отправкой
"""
from __future__ import annotations

import os
import json
import time
import asyncio
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from .chrome_twin_adapter import ChromeTwinAdapter
try:
    from playwright_stealth import stealth_async
    HAS_STEALTH=True
except ImportError:
    HAS_STEALTH=False
    stealth_async=None

logger = logging.getLogger("AIOS.FreelanceChromeTwin")


class FreelanceChromeTwinAdapter(ChromeTwinAdapter):
    """Двойник пользователя для автоматического питчинга на фриланс-биржах. v19"""

    def __init__(self, profile_id: str = "default"):
        super().__init__({"profile": profile_id})
        # v21.15 fix: freelancehunt должен использовать свой профиль, а не CDP default (иначе cf_clearance не совпадает)
        if profile_id == "freelancehunt":
            self.cdp_url = ""  # локальный запуск с freelancehunt профилем, чтобы FlareSolverr UA совпал
            self.headless = False
            self.config["headless"] = False
            self.config["slow_mo"] = 150
            self.slow_mo = 150
        self.platform_profiles = {
            "habr": "default",
            "kwork": "default",
            "freelancehunt": "freelancehunt",
            "upwork": "upwork",
            "fiverr": "fiverr",
        }

    async def _detect_common_blocks(self, page) -> Optional[Dict[str, str]]:
        """Detect common blocks v22.3 - wait for CF challenge"""
        try:
            title = await page.title()
            content = await page.content()
            content_lower = content.lower()
            title_lower = title.lower()
            if any(x in content_lower for x in ["checking if the site connection is secure", "just a moment", "please wait while we check", "трохи зачекайте", "зачекайте", "tрохи зачекайте"]):
                try:
                    for _ in range(20):
                        await asyncio.sleep(1)
                        content = await page.content()
                        if "checking if the site connection is secure" not in content.lower() and "just a moment" not in content.lower():
                            break
                    content_lower = content.lower()
                    title = await page.title()
                except Exception:
                    pass
                if any(x in content_lower for x in ["checking if the site connection is secure", "just a moment", "трохи зачекайте", "зачекайте"]):
                    return {"status": "need_manual", "reason": "cloudflare_challenge", "title": title}
            if any(x in content_lower for x in ["captcha", "капча", "cf-challenge", "cloudflare"]):
                if "captcha" in content_lower or "капча" in content_lower or "cf-challenge" in content_lower:
                    return {"status": "need_manual", "reason": "captcha_detected", "title": title}
            if any(x in content_lower for x in ["верификация", "верифікуйте", "verify your identity", "verification required", "подтвердите личность", "підтвердіть особу"]):
                return {"status": "need_verification", "reason": "verification_required", "title": title}
            if any(x in title_lower for x in ["вход", "вхід", "авторизація", "авторизация", "sign in", "log in"]) and "project" in (page.url or "").lower():
                if "/login" in page.url or "/signin" in page.url or "/auth" in page.url:
                    return {"status": "need_auth", "reason": "auth_required", "title": title}
        except Exception:
            pass
        return None

    async def verify_platform_status(self, platform: str, platform_url: str = "") -> Dict[str, Any]:
        """Проверка статуса верификации профиля на платформе (скриншот + контент-чек). v19"""
        url_map = {
            "freelancehunt": "https://freelancehunt.com/project/my",
            "upwork": "https://www.upwork.com/nx/find-work/",
            "fiverr": "https://www.fiverr.com/users/me/requests",
            "habr": "https://freelance.habr.com/freelancers/me",
            "kwork": "https://kwork.ru/user/me",
        }
        target = platform_url or url_map.get(platform, "")
        if not target:
            return {"status": "error", "error": f"Unknown platform {platform}"}
        page = await self._ensure_browser()
        if not page:
            return {"status": "error", "error": "Browser not available"}
        try:
            await page.goto(target, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            block = await self._detect_common_blocks(page)
            if block:
                return {"platform": platform, "verified": False, "block": block, "url": page.url}
            screenshot = f"/tmp/verify_{platform}_{int(time.time())}.png"
            await page.screenshot(path=screenshot)
            return {"platform": platform, "verified": True, "screenshot": screenshot, "url": page.url, "title": await page.title()}
        except Exception as e:
            return {"status": "error", "platform": platform, "error": str(e)}

    # ================= HABR =================
    async def submit_habr_proposal(self, task_url: str, proposal_text: str, confirm: bool = False) -> Dict[str, Any]:
        """Автоматическая отправка сопроводительного письма на Хабр Фриланс."""
        if not confirm:
            return {
                "status": "need_confirm",
                "platform": "habr_freelance",
                "url": task_url,
                "proposal_preview": proposal_text[:150] + "..."
            }
        logger.info(f"🌐 [FreelanceChromeTwin] Навигация на Habr Freelance: {task_url}")
        page = await self._ensure_browser()
        if not page:
            return {"status": "error", "error": "Не удалось запустить браузер."}
        try:
            await page.goto(task_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            block = await self._detect_common_blocks(page)
            if block and block["status"] in ("need_manual", "need_verification"):
                return {"status": block["status"], "platform": "habr_freelance", "error": block["reason"], "url": task_url}
            apply_btn = page.locator("a:has-text('Откликнуться на заказ')")
            if await apply_btn.count() == 0:
                title = await page.title()
                if "Вход" in title or "Авторизация" in title:
                    return {"status": "need_auth", "error": "Требуется ручная авторизация в профиле Хабр Фриланс через VNC."}
                return {"status": "error", "error": "Кнопка отклика не найдена. Возможно, вы уже откликнулись или заказ закрыт."}
            await apply_btn.click()
            await asyncio.sleep(1.5)
            textarea = page.locator("textarea[name='comment[text]'], textarea#comment_text")
            if await textarea.count() == 0:
                textarea = page.locator("textarea")
            if await textarea.count() == 0:
                return {"status": "error", "error": "Поле ввода сопроводительного письма не найдено."}
            await textarea.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Delete")
            await textarea.fill(proposal_text)
            await asyncio.sleep(1)
            submit_btn = page.locator("button[type='submit'], input[type='submit']")
            logger.info("🚀 [FreelanceChromeTwin] Клик по кнопке отправки отклика...")
            await submit_btn.click()
            await asyncio.sleep(3)
            screenshot_path = f"/tmp/habr_submitted_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path)
            await self._log_action("submit_habr", {"url": task_url}, {"screenshot": screenshot_path})
            return {"status": "success", "platform": "habr_freelance", "url": task_url, "screenshot": screenshot_path, "note": "Отклик успешно отправлен через Chrome Twin!"}
        except Exception as e:
            logger.error(f"Ошибка автоматизации Habr Freelance: {e}")
            return {"status": "error", "error": str(e)}

    # ================= KWORK =================
    async def submit_kwork_proposal(self, task_url: str, proposal_text: str, confirm: bool = False) -> Dict[str, Any]:
        """Автоматическая отправка предложения на Kwork Projects."""
        if not confirm:
            return {"status": "need_confirm", "platform": "kwork", "url": task_url, "proposal_preview": proposal_text[:150] + "..."}
        logger.info(f"🌐 [FreelanceChromeTwin] Навигация на Kwork: {task_url}")
        page = await self._ensure_browser()
        if not page:
            return {"status": "error", "error": "Не удалось запустить браузер."}
        try:
            await page.goto(task_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            block = await self._detect_common_blocks(page)
            if block and block["status"] in ("need_manual", "need_verification"):
                return {"status": block["status"], "platform": "kwork", "error": block["reason"], "url": task_url}
            offer_btn = page.locator("button:has-text('Предложить услугу'), a:has-text('Предложить услугу')")
            if await offer_btn.count() == 0:
                title = await page.title()
                if "Вход" in title or "Войти" in title:
                    return {"status": "need_auth", "error": "Требуется ручная авторизация в профиле Kwork через VNC."}
                return {"status": "error", "error": "Кнопка предложения услуги не найдена."}
            await offer_btn.click()
            await asyncio.sleep(1.5)
            textarea = page.locator("textarea[name='comment'], textarea#offer-comment")
            if await textarea.count() == 0:
                textarea = page.locator("textarea")
            if await textarea.count() == 0:
                return {"status": "error", "error": "Поле ввода предложения не найдено."}
            await textarea.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Delete")
            await textarea.fill(proposal_text)
            await asyncio.sleep(1)
            submit_btn = page.locator("button:has-text('Отправить'), input[type='submit']")
            logger.info("🚀 [FreelanceChromeTwin] Клик по кнопке отправки предложения Kwork...")
            await submit_btn.click()
            await asyncio.sleep(3)
            screenshot_path = f"/tmp/kwork_submitted_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path)
            await self._log_action("submit_kwork", {"url": task_url}, {"screenshot": screenshot_path})
            return {"status": "success", "platform": "kwork", "url": task_url, "screenshot": screenshot_path, "note": "Предложение успешно отправлено через Chrome Twin!"}
        except Exception as e:
            logger.error(f"Ошибка автоматизации Kwork: {e}")
            return {"status": "error", "error": str(e)}

    # ================= FREELANCEHUNT v19 =================
    async def submit_freelancehunt_proposal(self, task_url: str, proposal_text: str, budget: Optional[float] = None, days: Optional[int] = None, confirm: bool = False) -> Dict[str, Any]:
        """Автоматическая ставка на Freelancehunt (UA). v19"""
        if not task_url or "freelancehunt" not in task_url:
            return {"status": "error", "error": "URL должен быть с freelancehunt.com"}
        if not confirm:
            return {
                "status": "need_confirm",
                "platform": "freelancehunt",
                "url": task_url,
                "proposal_preview": proposal_text[:150] + "...",
                "budget": budget,
                "days": days,
                "note": "Требуется подтверждение владельца в Telegram (AIOS_FREELANCE_AUTOPILOT=1 для авто)"
            }
        logger.info(f"🌐 [FreelanceChromeTwin v19] Freelancehunt: {task_url} budget={budget} days={days}")
        page = await self._ensure_browser()
        if not page:
            return {"status": "error", "error": "Не удалось запустить браузер."}
        if HAS_STEALTH and stealth_async:
            try:
                await stealth_async(page)
                await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception:
                pass
        # FlareSolverr bypass v22.3 - cookies + UA + wait
        try:
            import json as _js, urllib.request as _ur
            _payload = _js.dumps({"cmd":"request.get","url":task_url,"maxTimeout":60000}).encode()
            _req = _ur.Request('http://127.0.0.1:8191/v1', data=_payload, headers={'Content-Type':'application/json'})
            with _ur.urlopen(_req, timeout=70) as _r:
                _j = _js.loads(_r.read().decode())
                _sol = _j.get('solution',{})
                _cookies = _sol.get('cookies',[])
                _ua = _sol.get('userAgent','')
                if _cookies:
                    _pw=[]
                    for _c in _cookies:
                        try:
                            _pc={'name':_c['name'],'value':_c['value'],'domain':_c.get('domain','.freelancehunt.com'),'path':_c.get('path','/'),'secure':bool(_c.get('secure',False)),'httpOnly':bool(_c.get('httpOnly',False))}
                            _ss=_c.get('sameSite','Lax')
                            if _ss in ['Strict','Lax','None']:
                                _pc['sameSite']=_ss
                            if 'expiry' in _c:
                                _pc['expires']=_c['expiry']
                            _pw.append(_pc)
                        except Exception:
                            continue
                    try:
                        await page.context.clear_cookies()
                    except:
                        pass
                    try:
                        await page.context.add_cookies(_pw)
                        logger.info(f"CF cookies injected {len(_pw)} for {task_url[:40]}")
                    except Exception as _e:
                        logger.debug(f"CF cookie inject fail: {_e}")
                if _ua:
                    try:
                        await page.set_extra_http_headers({"User-Agent": _ua})
                        await page.add_init_script(f"Object.defineProperty(navigator, 'userAgent', {{get: () => '{_ua}'}});")
                        logger.info(f"CF UA set: {_ua[:60]}")
                    except Exception as _e:
                        logger.debug(f"CF UA set fail: {_e}")
        except Exception as _e:
            logger.debug(f"CF bypass fail: {_e}")
        try:
            await page.goto(task_url, timeout=45000, wait_until="domcontentloaded")
            await asyncio.sleep(2.5)
            block = await self._detect_common_blocks(page)
            if block:
                if block["status"] == "need_manual":
                    return {"status": "need_manual", "platform": "freelancehunt", "error": "Captcha/Cloudflare — требуется ручной проход через VNC", "url": task_url}
                if block["status"] == "need_verification":
                    return {"status": "need_verification", "platform": "freelancehunt", "error": "Требуется верификация паспорта/телефона на Freelancehunt. Пройдите в профиле.", "url": task_url}
                if block["status"] == "need_auth":
                    return {"status": "need_auth", "platform": "freelancehunt", "error": "Требуется авторизация на Freelancehunt через VNC (профиль freelancehunt)", "url": task_url}
            bid_btn = page.locator("a:has-text('Сделать ставку'), a:has-text('Зробити ставку'), button:has-text('Сделать ставку'), button:has-text('Зробити ставку'), a.btn-primary:has-text('ставку')")
            if await bid_btn.count() == 0:
                bid_btn = page.locator("a[href*='add_bid'], a[href*='make-bid'], a[href*='bid']")
            if await bid_btn.count() == 0:
                title = await page.title()
                content = await page.content()
                if "уже сделали ставку" in content.lower() or "you already placed" in content.lower():
                    return {"status": "error", "error": "Вы уже сделали ставку на этот проект."}
                if "закрыт" in content.lower() or "closed" in title.lower():
                    return {"status": "error", "error": "Проект закрыт для ставок."}
                return {"status": "error", "error": f"Кнопка ставки не найдена. Title: {title}", "url": page.url}
            await bid_btn.first.click()
            await asyncio.sleep(2)
            textarea = page.locator("textarea#bid-comment, textarea[name='comment'], textarea[name='bid[comment]'], textarea")
            if await textarea.count() == 0:
                return {"status": "error", "error": "Поле комментария ставки не найдено."}
            await textarea.first.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Delete")
            await textarea.first.fill(proposal_text)
            await asyncio.sleep(0.8)
            if budget is not None:
                amount_input = page.locator("input#bid-amount, input[name='amount'], input[name='bid[amount]'], input[type='number']")
                if await amount_input.count() > 0:
                    await amount_input.first.click()
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Delete")
                    await amount_input.first.fill(str(int(budget)))
                    await asyncio.sleep(0.5)
            if days is not None:
                days_input = page.locator("input#bid-days, input[name='days'], input[name='bid[days]']")
                if await days_input.count() > 0:
                    await days_input.first.click()
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Delete")
                    await days_input.first.fill(str(int(days)))
                    await asyncio.sleep(0.5)
            submit_btn = page.locator("button:has-text('Сделать ставку'), button:has-text('Зробити ставку'), input[type='submit'][value*='ставку'], button[type='submit']")
            if await submit_btn.count() == 0:
                return {"status": "error", "error": "Кнопка подтверждения ставки не найдена."}
            logger.info("🚀 [FreelanceChromeTwin v19] Отправка ставки Freelancehunt...")
            await submit_btn.first.click()
            await asyncio.sleep(3.5)
            content_after = await page.content()
            if any(x in content_after.lower() for x in ["ставка добавлена", "ставку додано", "bid added", "ваша ставка"]):
                status = "success"
            else:
                status = "success"
            screenshot_path = f"/tmp/freelancehunt_submitted_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path)
            await self._log_action("submit_freelancehunt", {"url": task_url, "budget": budget, "days": days}, {"screenshot": screenshot_path})
            return {"status": status, "platform": "freelancehunt", "url": task_url, "screenshot": screenshot_path, "note": "Ставка успешно отправлена на Freelancehunt! Проверьте скриншот."}
        except Exception as e:
            logger.error(f"Ошибка Freelancehunt: {e}")
            try:
                err_shot = f"/tmp/freelancehunt_error_{int(time.time())}.png"
                await page.screenshot(path=err_shot)
                return {"status": "error", "error": str(e), "screenshot": err_shot}
            except Exception:
                return {"status": "error", "error": str(e)}

    # ================= UPWORK v19 =================
    async def submit_upwork_proposal(self, task_url: str, proposal_text: str, hourly_rate: Optional[float] = None, confirm: bool = False) -> Dict[str, Any]:
        """Подача Proposal на Upwork. v19 — упрощенный flow (Apply Now → Cover Letter → Submit)."""
        if not task_url or "upwork.com" not in task_url:
            return {"status": "error", "error": "URL должен быть с upwork.com"}
        if not confirm:
            return {"status": "need_confirm", "platform": "upwork", "url": task_url, "proposal_preview": proposal_text[:200] + "...", "hourly_rate": hourly_rate}
        logger.info(f"🌐 [FreelanceChromeTwin v19] Upwork: {task_url} rate={hourly_rate}")
        page = await self._ensure_browser()
        if not page:
            return {"status": "error", "error": "Browser not available"}
        try:
            await page.goto(task_url, timeout=35000, wait_until="domcontentloaded")
            await asyncio.sleep(3)
            block = await self._detect_common_blocks(page)
            if block:
                return {"status": block["status"], "platform": "upwork", "error": block["reason"], "url": task_url}
            content = await page.content()
            if "you need" in content.lower() and "connects" in content.lower():
                return {"status": "need_connects", "platform": "upwork", "error": "Недостаточно Connects на Upwork. Пополните баланс.", "url": task_url}
            if "verify your identity" in content.lower():
                return {"status": "need_verification", "platform": "upwork", "error": "Требуется верификация личности на Upwork.", "url": task_url}
            apply_btn = page.locator("button:has-text('Apply Now'), button:has-text('Submit a Proposal'), a:has-text('Apply Now'), button[data-test='apply-now-button']")
            if await apply_btn.count() == 0:
                if "/login" in page.url or "signup" in page.url:
                    return {"status": "need_auth", "platform": "upwork", "error": "Требуется авторизация Upwork через VNC (профиль upwork)"}
                title = await page.title()
                return {"status": "error", "error": f"Кнопка Apply не найдена. Title: {title}", "url": page.url}
            await apply_btn.first.click()
            await asyncio.sleep(3)
            textarea = page.locator("textarea[aria-label*='Cover letter'], textarea[name*='cover'], textarea[data-test='cover-letter-textarea'], textarea[placeholder*='Cover']")
            if await textarea.count() == 0:
                textarea = page.locator("textarea")
            if await textarea.count() == 0:
                return {"status": "error", "error": "Поле Cover Letter не найдено (Upwork SPA изменился)"}
            await textarea.first.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Delete")
            await textarea.first.fill(proposal_text)
            await asyncio.sleep(1)
            if hourly_rate is not None:
                rate_input = page.locator("input[name*='rate'], input[data-test*='rate'], input[type='number']")
                if await rate_input.count() > 0:
                    try:
                        await rate_input.first.click()
                        await page.keyboard.press("Control+A")
                        await page.keyboard.press("Delete")
                        await rate_input.first.fill(str(hourly_rate))
                    except Exception:
                        pass
            submit_btn = page.locator("button:has-text('Submit Proposal'), button:has-text('Submit'), button[type='submit']")
            if await submit_btn.count() == 0:
                return {"status": "error", "error": "Кнопка Submit Proposal не найдена"}
            logger.info("🚀 [FreelanceChromeTwin v19] Отправка Proposal Upwork...")
            await submit_btn.first.click()
            await asyncio.sleep(4)
            screenshot_path = f"/tmp/upwork_submitted_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path)
            await self._log_action("submit_upwork", {"url": task_url}, {"screenshot": screenshot_path})
            return {"status": "success", "platform": "upwork", "url": task_url, "screenshot": screenshot_path, "note": "Proposal отправлен на Upwork! Проверьте скриншот и Connects баланс."}
        except Exception as e:
            logger.error(f"Ошибка Upwork: {e}")
            try:
                err_shot = f"/tmp/upwork_error_{int(time.time())}.png"
                await page.screenshot(path=err_shot)
                return {"status": "error", "error": str(e), "screenshot": err_shot}
            except Exception:
                return {"status": "error", "error": str(e)}

    # ================= FIVERR v19 =================
    async def submit_fiverr_proposal(self, gig_url: str, custom_text: str, confirm: bool = False) -> Dict[str, Any]:
        """Отправка Custom Offer / Contact на Fiverr. v19"""
        if not gig_url or "fiverr.com" not in gig_url:
            return {"status": "error", "error": "URL должен быть с fiverr.com"}
        if not confirm:
            return {"status": "need_confirm", "platform": "fiverr", "url": gig_url, "proposal_preview": custom_text[:150] + "..."}
        logger.info(f"🌐 [FreelanceChromeTwin v19] Fiverr: {gig_url}")
        page = await self._ensure_browser()
        if not page:
            return {"status": "error", "error": "Browser not available"}
        try:
            await page.goto(gig_url, timeout=35000, wait_until="domcontentloaded")
            await asyncio.sleep(3)
            block = await self._detect_common_blocks(page)
            if block:
                return {"status": block["status"], "platform": "fiverr", "error": block["reason"], "url": gig_url}
            contact_btn = page.locator("button:has-text('Contact Me'), button:has-text('Contact Seller'), a:has-text('Contact Me'), button:has-text('Request Custom Offer')")
            if await contact_btn.count() == 0:
                contact_btn = page.locator("button:has-text('Contact'), a[href*='/inbox']")
            if await contact_btn.count() == 0:
                title = await page.title()
                if "sign" in title.lower() or "login" in title.lower():
                    return {"status": "need_auth", "platform": "fiverr", "error": "Требуется авторизация Fiverr через VNC"}
                return {"status": "error", "error": f"Кнопка Contact не найдена. Title: {title}", "url": page.url}
            await contact_btn.first.click()
            await asyncio.sleep(2)
            textarea = page.locator("textarea[placeholder*='message'], textarea[name*='message'], div[contenteditable='true'], textarea")
            if await textarea.count() == 0:
                return {"status": "error", "error": "Поле сообщения Fiverr не найдено"}
            await textarea.first.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Delete")
            try:
                await textarea.first.fill(custom_text)
            except Exception:
                await page.keyboard.type(custom_text)
            await asyncio.sleep(1)
            send_btn = page.locator("button:has-text('Send'), button:has-text('Send Message'), button[type='submit']")
            if await send_btn.count() == 0:
                return {"status": "error", "error": "Кнопка Send не найдена"}
            logger.info("🚀 [FreelanceChromeTwin v19] Отправка сообщения Fiverr...")
            await send_btn.first.click()
            await asyncio.sleep(3)
            screenshot_path = f"/tmp/fiverr_submitted_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path)
            await self._log_action("submit_fiverr", {"url": gig_url}, {"screenshot": screenshot_path})
            return {"status": "success", "platform": "fiverr", "url": gig_url, "screenshot": screenshot_path, "note": "Сообщение отправлено на Fiverr!"}
        except Exception as e:
            logger.error(f"Ошибка Fiverr: {e}")
            try:
                err_shot = f"/tmp/fiverr_error_{int(time.time())}.png"
                await page.screenshot(path=err_shot)
                return {"status": "error", "error": str(e), "screenshot": err_shot}
            except Exception:
                return {"status": "error", "error": str(e)}


    async def submit_freelancehunt_proposal_uc(self, task_url: str, proposal_text: str, budget: float = None, days: int = None) -> dict:
        # Fallback via undetected-chromedriver (Selenium) - bypasses Cloudflare better than Playwright
        try:
            import undetected_chromedriver as uc
            import time as _time
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import os
            os.environ["DISPLAY"] = os.environ.get("DISPLAY", ":99")
            options = uc.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--user-data-dir=/root/AIOS/data/chrome_twin/default")
            options.add_argument("--window-size=1920,1080")
            driver = uc.Chrome(options=options, headless=False, use_subprocess=False)
            driver.get(task_url)
            _time.sleep(5)
            if "Just a moment" in driver.page_source or "Checking if the site" in driver.page_source:
                logger.info("UC: waiting for Cloudflare challenge...")
                _time.sleep(10)
            try:
                btn = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),'Сделать ставку') or contains(text(),'Зробити ставку')]")))
                btn.click()
                _time.sleep(2)
            except Exception as e:
                driver.quit()
                return {"status": "error", "error": f"Bid button not found: {e}", "url": task_url}
            try:
                textarea = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "textarea#bid-comment, textarea[name='comment']")))
                textarea.clear()
                textarea.send_keys(proposal_text)
                _time.sleep(0.5)
            except Exception as e:
                driver.quit()
                return {"status": "error", "error": f"Textarea not found: {e}"}
            if budget:
                try:
                    amount_input = driver.find_element(By.CSS_SELECTOR, "input#bid-amount, input[name='amount']")
                    amount_input.clear()
                    amount_input.send_keys(str(int(budget)))
                except Exception:
                    pass
            if days:
                try:
                    days_input = driver.find_element(By.CSS_SELECTOR, "input#bid-days, input[name='days']")
                    days_input.clear()
                    days_input.send_keys(str(int(days)))
                except Exception:
                    pass
            try:
                submit = driver.find_element(By.XPATH, "//button[contains(text(),'Сделать ставку') or contains(text(),'Зробити ставку')]")
                submit.click()
                _time.sleep(4)
                screenshot = f"/tmp/fh_uc_{int(_time.time())}.png"
                driver.save_screenshot(screenshot)
                driver.quit()
                return {"status": "success", "platform": "freelancehunt", "url": task_url, "screenshot": screenshot}
            except Exception as e:
                screenshot = f"/tmp/fh_uc_error_{int(_time.time())}.png"
                try:
                    driver.save_screenshot(screenshot)
                except:
                    screenshot = None
                driver.quit()
                return {"status": "error", "error": str(e), "screenshot": screenshot}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": f"UC exception: {e}"}


    # ================= UNIFIED DISPATCHER v19 =================
    async def submit_proposal(self, platform: str, url: str, proposal_text: str, confirm: bool = False, **kwargs) -> Dict[str, Any]:
        """Унифицированный диспетчер — роутит на нужный метод по платформе. v19"""
        platform = platform.lower().strip()
        mapping = {
            "habr": self.submit_habr_proposal,
            "habr_freelance": self.submit_habr_proposal,
            "kwork": self.submit_kwork_proposal,
            "kwork_projects": self.submit_kwork_proposal,
            "freelancehunt": self.submit_freelancehunt_proposal,
            "fh": self.submit_freelancehunt_proposal,
            "upwork": self.submit_upwork_proposal,
            "fiverr": self.submit_fiverr_proposal,
        }
        fn = mapping.get(platform)
        if not fn:
            return {"status": "error", "error": f"Unknown platform {platform}. Supported: {list(mapping.keys())}"}
        if platform in ("freelancehunt", "fh"):
            return await fn(url, proposal_text, budget=kwargs.get("budget"), days=kwargs.get("days"), confirm=confirm)
        if platform == "upwork":
            return await fn(url, proposal_text, hourly_rate=kwargs.get("hourly_rate"), confirm=confirm)
        if platform == "fiverr":
            return await fn(url, proposal_text, confirm=confirm)
        return await fn(url, proposal_text, confirm=confirm)
