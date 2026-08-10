#!/usr/bin/env python3
"""
AIOS Google Colab Automated Runner & Activity Keeper (CDP 9222)
Запускает кодинг-модель в Google Colab через ваш текущий авторизованный браузер Chrome (CDP 9222),
извлекает публичный URL туннеля и поддерживает постоянную активность страницы,
чтобы сессия Colab не отключалась!
"""

import os
import sys
import time
import re
import json
import subprocess
import asyncio
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

os.environ["DISPLAY"] = os.environ.get("DISPLAY", ":1")


async def run_colab_automation():
    print("🚀 [ColabRunner] Запуск автоматизации Google Colab через Chrome CDP (9222)...")

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        from playwright.async_api import async_playwright

    default_nb = "https://colab.research.google.com/github/JoTalbot/AIOS/blob/main/docs/AIOS_Google_Colab_Whisper_Transcriber.ipynb" if "whisper" in sys.argv else "https://colab.research.google.com/github/JoTalbot/AIOS/blob/main/docs/AIOS_Google_Colab_LLM_Coding.ipynb"
    notebook_url = os.getenv("COLAB_NOTEBOOK_URL", default_nb)
    cdp_url = "http://localhost:9222"

    async with async_playwright() as p:
        browser = None
        context = None

        # 1. Попытка подключения к запущенному Chrome по CDP 9222
        try:
            print(f"📡 Подключение к браузеру Chrome по CDP: {cdp_url}...")
            browser = await p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            print("✅ Успешно подключились к запущенному Chrome по CDP!")
        except Exception as e:
            print(f"⚠️ CDP недоступен ({e}). Запускаю фоновый контекст Playwright...")
            user_data_dir = REPO_ROOT / "data" / "chrome_twin" / "default"
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=False,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )

        page = await context.new_page()
        await page.set_viewport_size({"width": 1920, "height": 1080})

        print(f"🔗 Переход в Google Colab Notebook: {notebook_url}")
        await page.goto(notebook_url, wait_until="networkidle", timeout=60000)
        print("✅ Страница Google Colab успешно загружена!")

        await asyncio.sleep(5)

        # Подключение GPU
        print("🔌 Проверка кнопки Подключиться к GPU...")
        try:
            connect_btn = page.locator("#connect, #reconnect")
            if await connect_btn.is_visible():
                await connect_btn.click()
                print("👍 Нажата кнопка Подключиться!")
                await asyncio.sleep(5)
        except Exception as e:
            print(f"Connect note: {e}")

        # Запуск всех ячеек (Ctrl+F9)
        print("▶️ Запуск выполнения всех ячеек (Ctrl+F9)...")
        await page.keyboard.press("Control+F9")
        await asyncio.sleep(5)

        # Окно 'Run anyway'
        try:
            run_anyway_btn = page.locator("colab-callout button, #ok")
            if await run_anyway_btn.is_visible():
                await run_anyway_btn.click()
                print("👍 Запуск ячеек подтвержден (Run anyway)!")
        except Exception:
            pass

        print("\n⏳ Ожидание инициализации vLLM и создания Cloudflare туннеля...")
        tunnel_url = ""

        for attempt in range(40): # До 4 минут ожидания
            await asyncio.sleep(6)
            page_text = await page.content()

            match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com/v1', page_text)
            if match:
                tunnel_url = match.group(0)
                print(f"\n🎉 ========================================================")
                print(f"🔗 ИЗВЛЕЧЁН ПУБЛИЧНЫЙ URL КОДИНГ-МОДЕЛИ ИЗ GOOGLE COLAB:")
                print(f"   {tunnel_url}")
                print(f"========================================================\n")
                break
            else:
                print(f"⏳ [Сканирование {attempt+1}/40] Ожидание генерации туннеля...")

        if tunnel_url:
            from scripts.register_colab_llm import register_colab_endpoint
            register_colab_endpoint(tunnel_url, "colab/qwen2.5-coder")
        else:
            print("⚠️ Ссылка туннеля пока не появилась в текстовом блоке. Переходим в режим вочдога активности...")

        # === БЕСКОНЕЧНЫЙ ЦИКЛ ПОДДЕРЖАНИЯ АКТИВНОСТИ (COLAB ACTIVITY KEEPER) ===
        print("\n🔄 [Colab Activity Keeper] Включен вочдог поддержания активности сессии Colab!")
        print("   Каждые 60 секунд отправляется колесо мыши и проверяются кнопки подключения, чтобы Colab не отключался.")

        click_counter = 0
        while True:
            await asyncio.sleep(60)
            click_counter += 1

            try:
                # 1. Движение и прокрутка колесом
                await page.mouse.wheel(0, 100)
                await asyncio.sleep(1)
                await page.mouse.wheel(0, -100)

                # 2. Проверка диалога отключения / переподключения
                rec_btn = page.locator("#connect, #reconnect")
                if await rec_btn.is_visible() and "connect" in (await rec_btn.text_content()).lower():
                    await rec_btn.click()
                    print(f"⚡ [Minute {click_counter}] Переподключена сессия Colab!")

                print(f"🟢 [Minute {click_counter}] Colab Activity Keeper: сессия активна.")
            except Exception as err:
                print(f"Activity loop note: {err}")


if __name__ == "__main__":
    try:
        asyncio.run(run_colab_automation())
    except KeyboardInterrupt:
        print("\n👋 Colab Automation остановлена.")
    except Exception as e:
        print(f"❌ Ошибка Colab Automation: {e}")
