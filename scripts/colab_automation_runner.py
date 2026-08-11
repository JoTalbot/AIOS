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
import secrets
import subprocess
import tempfile
import asyncio
import urllib.request
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


COLAB_KEYS_FILE = REPO_ROOT / "data" / ".llm_keys.json"
COLAB_ENV_FILE = REPO_ROOT / ".env"
COLAB_KEEPER_ENV_FILE = REPO_ROOT / "data" / ".colab_llm.env"
COLAB_MODEL = "colab/qwen2.5-coder"
_TUNNEL_PATTERN = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com/v1")


def _load_colab_runtime_config() -> dict:
    try:
        data = json.loads(COLAB_KEYS_FILE.read_text(encoding="utf-8"))
        config = data.get("colab_llm", {})
        return config if isinstance(config, dict) else {}
    except (OSError, ValueError):
        return {}


def _probe_colab_config(config: dict, *, timeout: float = 12) -> bool:
    """Cheap authenticated readiness check used before deciding to rerun cells."""
    base_url = str(config.get("base_url", "")).strip().rstrip("/")
    api_key = str(config.get("api_key", "")).strip()
    model = str(config.get("model", COLAB_MODEL)).strip() or COLAB_MODEL
    if not base_url or not api_key or config.get("enabled", True) is False:
        return False
    if not base_url.endswith("/v1"):
        base_url += "/v1"
    try:
        request = urllib.request.Request(
            base_url + "/models",
            headers={"Authorization": "Bearer " + api_key, "User-Agent": "AIOS-Colab-Keeper/2.0"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
        return model in {
            item.get("id") for item in payload.get("data", []) if isinstance(item, dict)
        }
    except Exception:
        return False


def _healthy_registered_colab() -> dict:
    if os.getenv("COLAB_REUSE_HEALTHY_ENDPOINT", "1").strip().lower() in ("0", "false", "no", "off"):
        return {}
    config = _load_colab_runtime_config()
    return config if _probe_colab_config(config) else {}


def _select_fresh_tunnel(
    urls: list[str], old_urls: set[str], output_was_cleared: bool
) -> str:
    """Reject stale notebook output left by an earlier Run all generation."""
    candidates = [url for url in urls if output_was_cleared or url not in old_urls]
    return candidates[-1] if candidates else ""


def _atomic_write(path: Path, content: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _update_env_values(path: Path, values: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(values)
    result: list[str] = []
    for line in lines:
        key = line.partition("=")[0] if "=" in line else ""
        if key in remaining:
            result.append(f"{key}={remaining.pop(key)}")
        else:
            result.append(line)
    result.extend(f"{key}={value}" for key, value in remaining.items())
    _atomic_write(path, "\n".join(result) + "\n")


def _rotate_colab_api_key() -> str:
    """Create a short-lived recovery generation key without logging its value."""
    current = os.getenv("COLAB_LLM_API_KEY", "").strip()
    enabled = os.getenv("COLAB_ROTATE_KEY_ON_RECOVERY", "1").strip().lower() not in (
        "0", "false", "no", "off"
    )
    if not enabled and current:
        return current
    new_key = secrets.token_urlsafe(36)
    os.environ["COLAB_LLM_API_KEY"] = new_key
    _update_env_values(COLAB_ENV_FILE, {"COLAB_LLM_API_KEY": new_key})
    _atomic_write(COLAB_KEEPER_ENV_FILE, "COLAB_LLM_API_KEY=" + new_key + "\n")
    print("🔐 Bearer-ключ Colab ротирован для нового recovery generation")
    return new_key


async def _connect_runtime(page) -> bool:
    """Connect through the current Colab shadow host and report final state."""
    try:
        state = page.locator("#connect, #reconnect")
        host = page.locator("colab-connect-button")
        tip = (await state.get_attribute("tooltiptext") or "") if await state.count() else ""
        connected = bool(re.search(r"Подключено к|Connected to", tip, re.I))
        if connected:
            print("✅ Runtime Colab уже подключён")
            return True
        if await host.is_visible():
            await host.click(timeout=5000)
            print("👍 Runtime Colab подключается/переподключается")
            await asyncio.sleep(10)
            tip = (await state.get_attribute("tooltiptext") or "") if await state.count() else ""
            return bool(re.search(r"Подключено к|Connected to", tip, re.I))
    except Exception as exc:
        print(f"Connect note: {type(exc).__name__}")
    return False


async def _output_text(page) -> str:
    """Read rendered outputs only; never read notebook sources containing secrets."""
    parts: list[str] = []
    try:
        parts.extend(await page.locator(".output-content, colab-error-output").all_inner_texts())
    except Exception:
        pass
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        try:
            parts.append(await frame.locator("body").inner_text(timeout=1000))
        except Exception:
            continue
    return "\n".join(parts)


async def _scrub_live_notebook_secret(page, api_key: str) -> bool:
    """Remove the bearer value from Monaco after the running process captured it."""
    if not api_key:
        return False
    try:
        changed = await page.evaluate("""([secret]) => {
          let changed = false;
          for (const model of monaco.editor.getModels()) {
            const value = model.getValue();
            if (!value.includes(secret)) continue;
            model.setValue(value.split(secret).join('__AIOS_RUNTIME_SECRET_SCRUBBED__'));
            changed = true;
          }
          return changed;
        }""", [api_key])
        if changed:
            print("🧹 Bearer-ключ удалён из live editor DOM после запуска")
        return bool(changed)
    except Exception:
        return False


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

        tunnel_url = ""
        colab_api_key = os.getenv("COLAB_LLM_API_KEY", "").strip()
        endpoint_reused = False
        old_tunnel_urls: set[str] = set()
        service_kind = os.getenv("COLAB_SERVICE_KIND", "llm")

        if reused:
            print("ℹ️  Вкладка переиспользована. Проверяю runtime и endpoint перед recovery...")
            reconnect_hit = await _confirm_dialogs(page)
            if reconnect_hit and re.search(r"повторно|reconnect", reconnect_hit, re.I):
                await asyncio.sleep(12)
            await _ensure_t4_runtime(page)
            await _connect_runtime(page)
            await _confirm_dialogs(page)
            await asyncio.sleep(2)

            if service_kind == "llm":
                healthy = await asyncio.to_thread(_healthy_registered_colab)
                if healthy:
                    tunnel_url = str(healthy.get("base_url", "")).strip().rstrip("/")
                    colab_api_key = str(healthy.get("api_key", "")).strip()
                    endpoint_reused = True
                    print("✅ Зарегистрированный Colab endpoint здоров; Run all пропущен")
                else:
                    colab_api_key = _rotate_colab_api_key()
                    await _prepare_llm_notebook(page)
                    old_tunnel_urls = set(_TUNNEL_PATTERN.findall(await _output_text(page)))
                    await page.keyboard.press("Control+F9")
                    print("▶️ Ctrl+F9 (Run all) отправлен для recovery")
                    await asyncio.sleep(3)
                    await _confirm_dialogs(page)
                    await asyncio.sleep(4)
            else:
                await page.keyboard.press("Control+F9")
                await asyncio.sleep(3)
                await _confirm_dialogs(page)
        else:
            print(f"🔗 Переход в Google Colab Notebook: {notebook_url}")
            await page.goto(notebook_url, wait_until="domcontentloaded", timeout=60000)
            print("✅ Страница Google Colab успешно загружена!")
            await asyncio.sleep(5)
            await _ensure_t4_runtime(page)
            await _connect_runtime(page)

            if service_kind == "llm":
                colab_api_key = _rotate_colab_api_key()
                await _prepare_llm_notebook(page)
                old_tunnel_urls = set(_TUNNEL_PATTERN.findall(await _output_text(page)))

            print("▶️ Запуск выполнения всех ячеек (Ctrl+F9)...")
            await page.keyboard.press("Control+F9")
            await asyncio.sleep(5)
            await _confirm_dialogs(page)
            await asyncio.sleep(4)

        print("\n⏳ Инициализация и слежение за выполнением...")

        # Туннель нужен только сервисам с cloudflared (LLM/Whisper).
        kind_needs_tunnel = service_kind in ("llm", "whisper")
        if kind_needs_tunnel and not tunnel_url:
            wait_attempts = int(os.getenv("COLAB_TUNNEL_WAIT_ATTEMPTS", "100"))
            output_was_cleared = not old_tunnel_urls
            for attempt in range(wait_attempts):
                await asyncio.sleep(6)
                output_text = await _output_text(page)

                if service_kind == "llm":
                    fatal_markers = (
                        "GPU available: False",
                        "T4 GPU не подключён",
                        "vLLM завершился:",
                        "vLLM не запустился за 8 минут",
                        "Cloudflare tunnel URL не получен",
                    )
                    if any(marker in output_text for marker in fatal_markers):
                        print("❌ Обнаружена фатальная ошибка LLM-ячейки; recovery будет перезапущен")
                        return
                    urls = _TUNNEL_PATTERN.findall(output_text)
                else:
                    urls = re.findall(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", output_text)

                if not urls:
                    output_was_cleared = True
                fresh_url = _select_fresh_tunnel(urls, old_tunnel_urls, output_was_cleared)
                if fresh_url:
                    tunnel_url = fresh_url
                    print("🎉 Получен URL нового выполнения tunnel-ячейки")
                    break
                print(f"⏳ [Сканирование {attempt + 1}/{wait_attempts}] Ожидание нового tunnel generation...")
        elif not kind_needs_tunnel:
            print("ℹ️  Этот ноутбук не создаёт туннель — переходим сразу к watchdog")

        if tunnel_url:
            if service_kind == "whisper" or "Whisper" in notebook_url:
                if not endpoint_reused:
                    from scripts.register_colab_whisper import register_whisper_endpoint
                    register_whisper_endpoint(tunnel_url)
            elif not endpoint_reused:
                from scripts.register_colab_llm import register_colab_endpoint
                register_colab_endpoint(
                    tunnel_url,
                    COLAB_MODEL,
                    api_key=colab_api_key,
                    verify=True,
                )
                await _scrub_live_notebook_secret(page, colab_api_key)
            else:
                print("♻️ Используется уже зарегистрированный здоровый endpoint")

            # AIOS Colab Farm registry is refreshed even on the idempotent path.
            try:
                from aios_core.colab.colab_registry import colab_registry
                kind_map = {"rl": "quant_ml", "clustering": "quant_ml", "lora": "llm", "gguf": "llm"}
                kind = kind_map.get(service_kind, service_kind)
                node = os.getenv("COLAB_NODE_ID", "local")
                name = os.getenv("COLAB_SERVICE_NAME", f"colab-{kind}")
                model = os.getenv("COLAB_LLM_MODEL", COLAB_MODEL) if kind == "llm" else None
                colab_registry.register(
                    kind=kind,
                    base_url=tunnel_url,
                    model=model,
                    name=name,
                    node_id=node,
                )
                print(f"📦 [ColabFarm] Сервис '{name}' ({kind}) зарегистрирован")
            except Exception as reg_err:
                print(f"⚠️ [ColabFarm] Регистрация не удалась: {type(reg_err).__name__}")
        elif kind_needs_tunnel:
            print("⚠️ Новый tunnel generation не появился; запускаю полный recovery")
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
                        headers = {"Authorization": "Bearer " + colab_api_key}
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
