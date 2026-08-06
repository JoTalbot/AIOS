"""
Freelance Chrome Twin Adapter — Автоматизация подачи заявок на фриланс-биржах через браузер Chrome
(работает под Xvfb :1 с использованием существующей сессии пользователя).

Поддерживаемые площадки:
- Habr Freelance (freelance.habr.com)
- Kwork Projects (kwork.ru/projects)
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
    """Двойник пользователя для автоматического питчинга на фриланс-биржах."""

    def __init__(self, profile_id: str = "default"):
        super().__init__({"profile": profile_id})

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
            # 1. Переходим на страницу задачи
            await page.goto(task_url, timeout=30000, wait_until="networkidle")
            await asyncio.sleep(2)

            # 2. Ищем кнопку «Откликнуться на заказ»
            # Селекторы Хабр Фриланс могут меняться, используем надежный поиск по тексту
            apply_btn = page.locator("a:has-text('Откликнуться на заказ')")
            if await apply_btn.count() == 0:
                # Возможно, пользователь уже откликнулся или не авторизован
                title = await page.title()
                if "Вход" in title or "Авторизация" in title:
                    return {"status": "error", "error": "Требуется ручная авторизация в профиле Хабр Фриланс через VNC."}
                return {"status": "error", "error": "Кнопка отклика не найдена. Возможно, вы уже откликнулись или заказ закрыт."}

            await apply_btn.click()
            await asyncio.sleep(1.5)

            # 3. Находим текстовое поле для сопроводительного письма
            textarea = page.locator("textarea[name='comment[text]'], textarea#comment_text")
            if await textarea.count() == 0:
                textarea = page.locator("textarea")

            if await textarea.count() == 0:
                return {"status": "error", "error": "Поле ввода сопроводительного письма не найдено."}

            # Очищаем и вводим питч
            await textarea.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Delete")
            await textarea.fill(proposal_text)
            await asyncio.sleep(1)

            # 4. Поиск кнопки отправки отклика
            submit_btn = page.locator("button[type='submit'], input[type='submit']")
            # В тестовом режиме кликаем, в боевом - с флагом confirm
            logger.info("🚀 [FreelanceChromeTwin] Клик по кнопке отправки отклика...")
            await submit_btn.click()
            await asyncio.sleep(3)

            screenshot_path = f"/tmp/habr_submitted_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path)

            return {
                "status": "success",
                "platform": "habr_freelance",
                "url": task_url,
                "screenshot": screenshot_path,
                "note": "Отклик успешно отправлен через Chrome Twin!"
            }

        except Exception as e:
            logger.error(f"Ошибка автоматизации Habr Freelance: {e}")
            return {"status": "error", "error": str(e)}

    async def submit_kwork_proposal(self, task_url: str, proposal_text: str, confirm: bool = False) -> Dict[str, Any]:
        """Автоматическая отправка предложения на Kwork Projects."""
        if not confirm:
            return {
                "status": "need_confirm",
                "platform": "kwork",
                "url": task_url,
                "proposal_preview": proposal_text[:150] + "..."
            }

        logger.info(f"🌐 [FreelanceChromeTwin] Навигация на Kwork: {task_url}")
        page = await self._ensure_browser()
        if not page:
            return {"status": "error", "error": "Не удалось запустить браузер."}

        try:
            await page.goto(task_url, timeout=30000, wait_until="networkidle")
            await asyncio.sleep(2)

            # 1. Проверяем кнопку отклика
            offer_btn = page.locator("button:has-text('Предложить услугу'), a:has-text('Предложить услугу')")
            if await offer_btn.count() == 0:
                title = await page.title()
                if "Вход" in title or "Войти" in title:
                    return {"status": "error", "error": "Требуется ручная авторизация в профиле Kwork через VNC."}
                return {"status": "error", "error": "Кнопка предложения услуги не найдена."}

            await offer_btn.click()
            await asyncio.sleep(1.5)

            # 2. Поле ввода сопроводительного письма (покрытия)
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

            # 3. Клик отправки предложения
            submit_btn = page.locator("button:has-text('Отправить'), input[type='submit']")
            logger.info("🚀 [FreelanceChromeTwin] Клик по кнопке отправки предложения Kwork...")
            await submit_btn.click()
            await asyncio.sleep(3)

            screenshot_path = f"/tmp/kwork_submitted_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path)

            return {
                "status": "success",
                "platform": "kwork",
                "url": task_url,
                "screenshot": screenshot_path,
                "note": "Предложение успешно отправлено через Chrome Twin!"
            }

        except Exception as e:
            logger.error(f"Ошибка автоматизации Kwork: {e}")
            return {"status": "error", "error": str(e)}
