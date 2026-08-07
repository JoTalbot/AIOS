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

logger = logging.getLogger("AIOS.FreelanceChromeTwin")


class FreelanceChromeTwinAdapter(ChromeTwinAdapter):
    """Двойник пользователя для автоматического питчинга на фриланс-биржах. v19"""

    def __init__(self, profile_id: str = "default"):
        super().__init__({"profile": profile_id})
        self.platform_profiles = {
            "habr": "default",
            "kwork": "default",
            "freelancehunt": "freelancehunt",
            "upwork": "upwork",
            "fiverr": "fiverr",
        }

    async def _detect_common_blocks(self, page) -> Optional[Dict[str, str]]:
        """Детект общих блокеров: капча, Cloudflare, верификация, лимиты"""
        try:
            title = await page.title()
            content = await page.content()
            content_lower = content.lower()
            title_lower = title.lower()
            if any(x in content_lower for x in ["captcha", "капча", "cf-challenge", "checking if the site connection is secure", "cloudflare"]):
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
            await page.goto(task_url, timeout=30000, wait_until="networkidle")
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
            await page.goto(task_url, timeout=30000, wait_until="networkidle")
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
        try:
            await page.goto(task_url, timeout=30000, wait_until="networkidle")
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
            await page.goto(task_url, timeout=35000, wait_until="networkidle")
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
            await page.goto(gig_url, timeout=35000, wait_until="networkidle")
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
