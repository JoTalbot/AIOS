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


# Ноутбуки Colab-фермы по типу сервиса (для авто-запуска через COLAB_SERVICE_KIND)
NOTEBOOK_MAP = {
    "llm":        "AIOS_Google_Colab_LLM_Coding.ipynb",
    "whisper":    "AIOS_Google_Colab_Whisper_Transcriber.ipynb",
    "quant_ml":   "AIOS_Colab_Quant_ML_Training.ipynb",
    "rl":         "AIOS_Colab_Quant_RL_Training.ipynb",
    "clustering": "AIOS_Colab_Quant_Clustering.ipynb",
    "lora":       "AIOS_Colab_LoRA_FineTune.ipynb",
    "embeddings": "AIOS_Colab_Embeddings_Build.ipynb",
    "scraper":    "AIOS_Colab_Scraper_Farm.ipynb",
    "gguf":       "AIOS_Colab_GGUF_Quantize.ipynb",
}
GITHUB_NB = "https://colab.research.google.com/github/JoTalbot/AIOS/blob/main/docs/"


def _pick_notebook() -> str:
    """Определить URL ноутбука по env-переменным / аргументам."""
    # 1) явный URL
    env_url = os.getenv("COLAB_NOTEBOOK_URL", "").strip()
    if env_url:
        return env_url
    # 2) локальный файл (если указан COLAB_NOTEBOOK_FILE)
    local_file = os.getenv("COLAB_NOTEBOOK_FILE", "").strip()
    if local_file and Path(local_file).exists():
        return f"file://{Path(local_file).resolve()}"
    # 3) по типу сервиса
    kind = os.getenv("COLAB_SERVICE_KIND", "")
    if kind in NOTEBOOK_MAP:
        return GITHUB_NB + NOTEBOOK_MAP[kind]
    # 4) fallback: whisper/llm по аргументам
    return (GITHUB_NB + "AIOS_Google_Colab_Whisper_Transcriber.ipynb"
            if "whisper" in sys.argv else GITHUB_NB + "AIOS_Google_Colab_LLM_Coding.ipynb")


async def run_colab_automation():
    print("🚀 [ColabRunner] Запуск автоматизации Google Colab через Chrome CDP (9222)...")

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        from playwright.async_api import async_playwright

    notebook_url = _pick_notebook()
    print(f"📒 Выбран ноутбук: {notebook_url}")
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
        await page.goto(notebook_url, wait_until="domcontentloaded", timeout=60000)
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

        # Окно 'Run anyway' / Подтверждение запуска
        await asyncio.sleep(2)
        try:
            for selector in [
                "button:has-text('Run anyway')",
                "button:has-text('Всё равно')",
                "button:has-text('Все равно')",
                "button:has-text('Запустить')",
                "colab-callout button",
                "#ok",
                "mwc-button#ok",
                "paper-button#ok"
            ]:
                try:
                    btn = page.locator(selector)
                    if await btn.is_visible(timeout=1000):
                        await btn.click()
                        print(f"👍 Запуск ячеек подтвержден ({selector})!")
                        break
                except Exception:
                    pass
        except Exception as _de:
            print(f"Dialog check note: {_de}")

        print("\n⏳ Ожидание инициализации vLLM и создания Cloudflare туннеля...")
        tunnel_url = ""

        for attempt in range(40): # До 4 минут ожидания
            await asyncio.sleep(6)
            page_text = await page.content()

            is_whisper_mode = "whisper" in sys.argv or "Whisper" in notebook_url
            pattern = r'https://[a-zA-Z0-9-]+\.trycloudflare\.com' if is_whisper_mode else r'https://[a-zA-Z0-9-]+\.trycloudflare\.com/v1'
            match = re.search(pattern, page_text)
            if match:
                tunnel_url = match.group(0)
                print(f"\n🎉 ========================================================")
                print(f"🔗 ИЗВЛЕЧЁН ПУБЛИЧНЫЙ URL ИЗ GOOGLE COLAB ({'Whisper' if is_whisper_mode else 'LLM'}):")
                print(f"   {tunnel_url}")
                print(f"========================================================\n")
                break
            else:
                print(f"⏳ [Сканирование {attempt+1}/40] Ожидание генерации туннеля...")

        if tunnel_url:
            if "whisper" in sys.argv or "Whisper" in notebook_url:
                from scripts.register_colab_whisper import register_whisper_endpoint
                register_whisper_endpoint(tunnel_url)
            else:
                from scripts.register_colab_llm import register_colab_endpoint
                register_colab_endpoint(tunnel_url, "colab/qwen2.5-coder")

            # === AIOS Colab Farm: регистрация в едином реестре (Этап 1) ===
            try:
                from aios_core.colab.colab_registry import colab_registry
                # маппинг ноутбучных типов на типы реестра
                kind_map = {"rl": "quant_ml", "clustering": "quant_ml", "lora": "llm", "gguf": "llm"}
                _k = os.getenv("COLAB_SERVICE_KIND",
                               "whisper" if ("whisper" in sys.argv or "Whisper" in notebook_url) else "llm")
                kind = kind_map.get(_k, _k)
                node = os.getenv("COLAB_NODE_ID", "local")
                name = os.getenv("COLAB_SERVICE_NAME", f"colab-{kind}")
                model = os.getenv("COLAB_LLM_MODEL", "colab/qwen2.5-coder") if kind == "llm" else None
                colab_registry.register(kind=kind, base_url=tunnel_url,
                                        model=model, name=name, node_id=node)
                print(f"📦 [ColabFarm] Сервис '{name}' ({kind}) зарегистрирован в реестре Colab-фермы.")
            except Exception as re:
                print(f"⚠️ [ColabFarm] Не удалось зарегистрировать сервис в реестре: {re}")
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
