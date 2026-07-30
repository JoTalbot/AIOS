"""Session check — quickly verify whether arena.ai is logged in."""
import sys, json, time, re
PROFILE = sys.argv[1]
from playwright.sync_api import sync_playwright
JS_TEXT = "() => document.body ? document.body.innerText.slice(0, 2000) : ''"
play = sync_playwright().start()
result = {"ok": False, "text": "", "error": None}
try:
    ctx = play.chromium.launch_persistent_context(
        user_data_dir=PROFILE, headless=True,
        viewport={"width": 1365, "height": 768},
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://arena.ai/", wait_until="domcontentloaded", timeout=30000)
    time.sleep(4)
    text = page.evaluate(JS_TEXT) or ""
    has_login = bool(re.search(r'^Log In$', text, re.M))
    result["text"] = "logged_in" if not has_login else "logged_out"
    result["ok"] = True
    ctx.close()
except Exception as e:
    result["error"] = type(e).__name__ + ": " + str(e)
finally:
    try: play.stop()
    except: pass
print(json.dumps(result, ensure_ascii=False))
