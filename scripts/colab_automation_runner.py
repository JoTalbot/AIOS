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



async def _confirm_dialogs(page):
    """Confirm known Colab dialogs, including reconnect and runtime changes."""
    js_confirm = """
    () => {
      const EXACT = [
        "Усе одно запустити", "Усе одно запустить", "Всё равно запустить",
        "Все равно запустить", "Выполнить", "Run anyway", "Run",
        "Подключиться повторно", "Підключитися повторно", "Reconnect",
        "Reconnect runtime", "Продолжить", "Continue", "ОК", "OK"
      ];
      const labels = EXACT.map(s => s.toLowerCase());
      let hit = null;
      const walk = root => {
        for (const el of root.querySelectorAll("*")) {
          if (hit) return;
          if (el.shadowRoot) walk(el.shadowRoot);
          const text = (el.innerText || el.textContent || "").trim();
          if (labels.includes(text.toLowerCase())) {
            el.click();
            hit = text;
          }
        }
      };
      const dialogs = Array.from(document.querySelectorAll(
        "mwc-dialog[open], md-dialog[open], paper-dialog[open]"
      ));
      if (dialogs.length) {
        for (const dialog of dialogs) {
          walk(dialog);
          if (hit) break;
        }
      } else {
        walk(document);
      }
      if (!hit) {
        for (const frame of document.querySelectorAll("iframe")) {
          try {
            if (frame.contentDocument) walk(frame.contentDocument);
          } catch (e) {}
          if (hit) break;
        }
      }
      return hit;
    }
    """
    try:
        hit = await page.evaluate(js_confirm)
        if hit:
            print(f"👍 Подтверждено (JS): {hit}")
            await asyncio.sleep(1)
        return hit
    except Exception:
        return None


async def _ensure_t4_runtime(page):
    """Select a T4 runtime for the LLM notebook without resetting an existing T4."""
    if os.getenv("COLAB_SERVICE_KIND", "llm") != "llm":
        return False
    if os.getenv("COLAB_AUTO_T4", "1").strip().lower() in ("0", "false", "no", "off"):
        return False

    try:
        # Clear reconnect/runtime warnings that would intercept the menu click.
        await _confirm_dialogs(page)
        menu = page.locator("#runtime-menu-button")
        await menu.click(timeout=5000)
        await asyncio.sleep(0.5)

        item = None
        for label in ("Сменить среду выполнения", "Change runtime type"):
            candidates = page.get_by_text(label, exact=True)
            for index in range(await candidates.count()):
                candidate = candidates.nth(index)
                if await candidate.is_visible():
                    item = candidate
                    break
            if item is not None:
                break
        if item is None:
            await page.keyboard.press("Escape")
            print("⚠️ Не найден пункт смены runtime; оставляю текущий тип")
            return False

        await item.click(timeout=5000)
        await asyncio.sleep(1)
        t4 = page.locator('mwc-radio[value="GPU,T4"]')
        if not await t4.count():
            await page.keyboard.press("Escape")
            print("⚠️ T4 недоступна в диалоге Colab")
            return False

        if await t4.evaluate("e => !!e.checked"):
            await page.evaluate("""() => {
              const dialog = document.querySelector('mwc-dialog.change-runtime-type[open]');
              if (!dialog) return;
              const walk = root => {
                for (const el of root.querySelectorAll('*')) {
                  if (el.shadowRoot) walk(el.shadowRoot);
                  const text = (el.innerText || el.textContent || '').trim();
                  if (text === 'Отмена' || text === 'Cancel') { el.click(); return; }
                }
              };
              walk(dialog);
            }""")
            print("✅ Runtime Colab уже настроен на T4")
            return False

        await t4.click(timeout=5000)
        if not await t4.evaluate("e => !!e.checked"):
            raise RuntimeError("T4 radio did not become checked")
        saved = await page.evaluate("""() => {
          const dialog = document.querySelector('mwc-dialog.change-runtime-type[open]');
          if (!dialog) return false;
          let hit = false;
          const walk = root => {
            for (const el of root.querySelectorAll('*')) {
              if (hit) return;
              if (el.shadowRoot) walk(el.shadowRoot);
              const text = (el.innerText || el.textContent || '').trim();
              if (text === 'Сохранить' || text === 'Save') { el.click(); hit = true; }
            }
          };
          walk(dialog);
          return hit;
        }""")
        if not saved:
            raise RuntimeError("runtime Save button not found")
        await asyncio.sleep(1)
        await _confirm_dialogs(page)
        await asyncio.sleep(12)
        print("✅ Runtime Colab автоматически переключён на T4")
        return True
    except Exception as exc:
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass
        print(f"⚠️ Auto-T4 note: {type(exc).__name__}: {str(exc)[:160]}")
        return False


async def _prepare_llm_notebook(page):
    """Patch the GitHub LLM notebook for the current Colab runtime.

    The upstream notebook used a non-existent PyPI ``cloudflared`` package and
    an unprotected full-precision model.  This runtime patch keeps the GitHub
    source generic while injecting the per-node API key only into the live,
    authenticated Colab session.
    """
    if os.getenv("COLAB_SERVICE_KIND", "llm") != "llm":
        return
    api_key = os.getenv("COLAB_LLM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("COLAB_LLM_API_KEY is required for the Colab LLM endpoint")

    cell1 = """# === Установка vLLM и cloudflared binary ===
!pip install -q vllm
!pip uninstall -y -q torchaudio
!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /usr/local/bin/cloudflared
!chmod +x /usr/local/bin/cloudflared
import subprocess
print("✅ vLLM и cloudflared установлены; конфликтующий torchaudio удалён")
subprocess.run(["cloudflared", "--version"], check=True)
"""
    cell2 = f"""# === Защищённый vLLM OpenAI API на T4 ===
import subprocess, time, requests, pathlib, torch
API_KEY = {api_key!r}
print("GPU available:", torch.cuda.is_available())
if not torch.cuda.is_available():
    raise RuntimeError("T4 GPU не подключён: torch.cuda.is_available() == False")
print("GPU:", torch.cuda.get_device_name(0))
subprocess.run("pkill -f 'vllm.entrypoints.openai.api_server' || true", shell=True)
log_path = "/tmp/aios_vllm.log"
log_file = open(log_path, "w")
cmd = [
    "python3", "-m", "vllm.entrypoints.openai.api_server",
    "--model", "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
    "--served-model-name", "colab/qwen2.5-coder",
    "--quantization", "awq", "--dtype", "half",
    "--port", "8000", "--max-model-len", "4096",
    "--gpu-memory-utilization", "0.90", "--api-key", API_KEY,
]
vllm_proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
headers = {{"Authorization": "Bearer " + API_KEY}}
for attempt in range(240):
    if vllm_proc.poll() is not None:
        log_file.flush()
        tail = pathlib.Path(log_path).read_text(errors="replace")[-5000:]
        raise RuntimeError("vLLM завершился:\\n" + tail)
    try:
        response = requests.get("http://127.0.0.1:8000/v1/models", headers=headers, timeout=3)
        if response.status_code == 200:
            print("✅ vLLM API готов: colab/qwen2.5-coder")
            break
    except Exception:
        pass
    if attempt % 10 == 0:
        print(f"⏳ Загрузка модели: {{attempt * 2}} сек")
    time.sleep(2)
else:
    log_file.flush()
    tail = pathlib.Path(log_path).read_text(errors="replace")[-5000:]
    raise TimeoutError("vLLM не запустился за 8 минут:\\n" + tail)
"""
    cell3 = """# === Защищённый Cloudflare tunnel ===
import subprocess, re, time
subprocess.run(["pkill", "-f", "cloudflared tunnel --url http://127.0.0.1:8000"], check=False)
time.sleep(1)
tunnel = subprocess.Popen(
    ["cloudflared", "tunnel", "--url", "http://127.0.0.1:8000", "--no-autoupdate"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
)
tunnel_url = ""
deadline = time.time() + 90
while time.time() < deadline:
    line = tunnel.stdout.readline()
    if not line and tunnel.poll() is not None:
        break
    match = re.search(r"https://[a-zA-Z0-9-]+\\.trycloudflare\\.com", line or "")
    if match:
        tunnel_url = match.group(0) + "/v1"
        print("🎉 COLAB_LLM_URL=" + tunnel_url)
        print("🔐 API защищён Bearer-ключом AIOS")
        break
if not tunnel_url:
    raise RuntimeError("Cloudflare tunnel URL не получен")
"""
    patch_js = """([c1,c2,c3]) => {
      const models = monaco.editor.getModels();
      const find = (patterns) => models.find(m => patterns.some(p => m.getLineContent(1).startsWith(p)));
      const m1 = find(['# === ЯЧЕЙКА 1', '# === Установка vLLM']);
      const m2 = find(['# === ЯЧЕЙКА 2', '# === Защищённый vLLM']);
      const m3 = find(['# === ЯЧЕЙКА 3', '# === Защищённый Cloudflare']);
      if (!m1 || !m2 || !m3) return false;
      m1.setValue(c1); m2.setValue(c2); m3.setValue(c3);
      return true;
    }"""
    for _ in range(20):
        try:
            if await page.evaluate(patch_js, [cell1, cell2, cell3]):
                print("🛠️ LLM-ячейки Colab подготовлены для T4/AWQ и защищённого API")
                return
        except Exception:
            pass
        await asyncio.sleep(1)
    raise RuntimeError("Не удалось подготовить LLM-ячейки Colab")


async def run_colab_automation():
    cdp_url = (
        os.getenv("COLAB_CDP_URL")
        or os.getenv("AIOS_CHROME_CDP")
        or "http://localhost:9222"
    )
    print(f"🚀 [ColabRunner] Запуск автоматизации Google Colab через Chrome CDP ({cdp_url})...")

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        from playwright.async_api import async_playwright

    notebook_url = _pick_notebook()
    print(f"📒 Выбран ноутбук: {notebook_url}")

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
            user_data_dir = Path(
                os.getenv(
                    "COLAB_CHROME_PROFILE",
                    str(REPO_ROOT / "data" / "chrome_twin" / "default"),
                )
            )
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=False,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )

        page = await context.new_page()
        await page.set_viewport_size({"width": 1920, "height": 1080})

        # Переиспользование уже открытой вкладки с тем же ноутбуком
        reused = False
        nb_key = notebook_url.split("/")[-1]
        for pg in context.pages:
            try:
                if nb_key and nb_key in pg.url and "colab" in pg.url:
                    page = pg
                    reused = True
                    print(f"✅ Переиспользована существующая вкладка Colab: {nb_key}")
                    break
            except Exception:
                continue

        if reused:
            print("ℹ️  Вкладка переиспользована. Проверяю runtime, подтверждаю диалоги и запускаю выполнение...")
            # Диалог истёкшей среды выполнения перехватывает клики по #connect.
            # Сначала подтверждаем Reconnect, затем повторно проверяем toolbar.
            reconnect_hit = await _confirm_dialogs(page)
            if reconnect_hit and re.search(r"повторно|reconnect", reconnect_hit, re.I):
                await asyncio.sleep(12)
            await _ensure_t4_runtime(page)
            # После смены CPU→GPU Colab оставляет вкладку открытой, но runtime отключён.
            # У кнопки внутри shadow DOM нет доступного текста, поэтому проверяем сам #connect.
            try:
                connect_state = page.locator("#connect, #reconnect")
                connect_host = page.locator("colab-connect-button")
                connect_tip = (await connect_state.get_attribute("tooltiptext") or "") if await connect_state.count() else ""
                already_connected = bool(re.search(r"Подключено к|Connected to", connect_tip, re.I))
                if await connect_host.is_visible() and not already_connected:
                    # The #connect control lives in shadow DOM; clicking it directly
                    # is intercepted by the colab-connect-button host in current Colab.
                    await connect_host.click(timeout=5000)
                    print("👍 Runtime Colab подключён/переподключён")
                    await asyncio.sleep(10)
                elif already_connected:
                    print("✅ Runtime Colab уже подключён")
            except Exception as connect_err:
                print(f"Connect note: {connect_err}")
            await _confirm_dialogs(page)
            await asyncio.sleep(2)
            await _prepare_llm_notebook(page)
            try:
                await page.keyboard.press("Control+F9")
                print("▶️ Ctrl+F9 (Run all) отправлен")
            except Exception as ex:
                print(f"Run note: {ex}")
            await asyncio.sleep(3)
            await _confirm_dialogs(page)
            await asyncio.sleep(4)
        else:
            print(f"🔗 Переход в Google Colab Notebook: {notebook_url}")
            await page.goto(notebook_url, wait_until="domcontentloaded", timeout=60000)
            print("✅ Страница Google Colab успешно загружена!")

            await asyncio.sleep(5)
            await _ensure_t4_runtime(page)
            await _prepare_llm_notebook(page)

            # Подключение GPU
            print("🔌 Проверка кнопки Подключиться к GPU...")
            try:
                connect_state = page.locator("#connect, #reconnect")
                connect_host = page.locator("colab-connect-button")
                connect_tip = (await connect_state.get_attribute("tooltiptext") or "") if await connect_state.count() else ""
                already_connected = bool(re.search(r"Подключено к|Connected to", connect_tip, re.I))
                if await connect_host.is_visible() and not already_connected:
                    await connect_host.click(timeout=5000)
                    print("👍 Нажата кнопка Подключиться!")
                    await asyncio.sleep(5)
                elif already_connected:
                    print("✅ Runtime Colab уже подключён")
            except Exception as e:
                print(f"Connect note: {e}")

            # Запуск всех ячеек (Ctrl+F9)
            print("▶️ Запуск выполнения всех ячеек (Ctrl+F9)...")
            await page.keyboard.press("Control+F9")
            await asyncio.sleep(5)

            # Окно 'Run anyway' / Подтверждение запуска (многоязычно)
            await asyncio.sleep(2)
            await _confirm_dialogs(page)

            # Повторный запуск, если диалог подтверждения сбросил выполнение
            await asyncio.sleep(2)
            try:
                await page.keyboard.press("Control+F9")
                print("▶️ Повторный Ctrl+F9 (Run all) после подтверждения")
            except Exception:
                pass
            await asyncio.sleep(3)
            await _confirm_dialogs(page)

        print("\n⏳ Инициализация и слежение за выполнением...")
        tunnel_url = ""

        # Туннель нужен только сервисам с cloudflared (LLM/Whisper).
        kind_needs_tunnel = os.getenv("COLAB_SERVICE_KIND", "llm") in ("llm", "whisper")
        if kind_needs_tunnel:
            wait_attempts = int(os.getenv("COLAB_TUNNEL_WAIT_ATTEMPTS", "100"))
            for attempt in range(wait_attempts):  # По умолчанию до 10 минут ожидания
                await asyncio.sleep(6)

                # Stop immediately on terminal cell errors instead of spending the
                # full tunnel timeout scanning a CPU or failed vLLM runtime. Read
                # output containers only: notebook sources contain the injected key.
                if os.getenv("COLAB_SERVICE_KIND", "llm") == "llm":
                    try:
                        output_parts = await page.locator(
                            ".output-content, colab-error-output"
                        ).all_inner_texts()
                        output_text = "\n".join(output_parts)
                        fatal_markers = (
                            "GPU available: False",
                            "T4 GPU не подключён",
                            "vLLM завершился:",
                            "vLLM не запустился за 8 минут",
                            "Cloudflare tunnel URL не получен",
                        )
                        if any(marker in output_text for marker in fatal_markers):
                            print("❌ Обнаружена фатальная ошибка LLM-ячейки; прекращаю scan-loop для recovery.")
                            return
                    except Exception as output_err:
                        print(f"Cell output check note: {type(output_err).__name__}")

                page_text = await page.content()
                # Выводы Colab рендерятся в отдельных googleusercontent iframe.
                # page.content() содержит только iframe-теги, поэтому читаем frames явно.
                for frame in page.frames:
                    if frame == page.main_frame:
                        continue
                    try:
                        page_text += "\n" + await frame.locator("body").inner_text(timeout=1500)
                    except Exception:
                        continue

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
                    print(f"⏳ [Сканирование {attempt+1}/{wait_attempts}] Ожидание генерации туннеля...")
        else:
            print("ℹ️  Этот ноутбук не создаёт туннель — переходим сразу к вочдогу.")

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
            except Exception as reg_err:
                print(f"⚠️ [ColabFarm] Не удалось зарегистрировать сервис в реестре: {reg_err}")
        else:
            print("⚠️ Ссылка туннеля не появилась. Завершаю попытку для полного перезапуска automation.")
            if kind_needs_tunnel:
                return

        # === БЕСКОНЕЧНЫЙ ЦИКЛ ПОДДЕРЖАНИЯ АКТИВНОСТИ (COLAB ACTIVITY KEEPER) ===
        print("\n🔄 [Colab Activity Keeper] Включен вочдог поддержания активности сессии Colab!")
        print("   Каждые 60 секунд отправляется колесо мыши и проверяются кнопки подключения, чтобы Colab не отключался.")

        click_counter = 0
        endpoint_failures = 0
        while True:
            await asyncio.sleep(60)
            click_counter += 1

            try:
                # 1. Движение и прокрутка колесом
                await page.mouse.wheel(0, 100)
                await asyncio.sleep(1)
                await page.mouse.wheel(0, -100)

                # 2. Проверка диалога отключения / переподключения
                rec_state = page.locator("#connect, #reconnect")
                rec_host = page.locator("colab-connect-button")
                rec_tip = (await rec_state.get_attribute("tooltiptext") or "") if await rec_state.count() else ""
                rec_connected = bool(re.search(r"Подключено к|Connected to", rec_tip, re.I))
                if await rec_host.is_visible() and not rec_connected:
                    reconnect_hit = await _confirm_dialogs(page)
                    if not reconnect_hit:
                        try:
                            await rec_host.click(timeout=5000)
                        except Exception:
                            pass
                    print(f"⚡ [Minute {click_counter}] Runtime Colab потерян; перезапускаю полную automation.")
                    return

                # Every two minutes verify that the protected LLM tunnel itself
                # is alive. Two consecutive failures trigger a full notebook rerun.
                is_llm_mode = "whisper" not in sys.argv and "Whisper" not in notebook_url
                if tunnel_url and is_llm_mode and click_counter % 2 == 0:
                    try:
                        import urllib.request as _ur
                        health_url = tunnel_url.rstrip("/") + "/models"
                        headers = {"Authorization": "Bearer " + os.getenv("COLAB_LLM_API_KEY", "")}
                        req = _ur.Request(health_url, headers=headers)
                        with _ur.urlopen(req, timeout=12) as response:
                            if response.status != 200:
                                raise RuntimeError(f"HTTP {response.status}")
                        endpoint_failures = 0
                    except Exception as health_err:
                        endpoint_failures += 1
                        print(f"⚠️ [Minute {click_counter}] Tunnel health failure {endpoint_failures}/2: {type(health_err).__name__}")
                        if endpoint_failures >= 2:
                            print("♻️ Tunnel недоступен; перезапускаю полную automation.")
                            return

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
