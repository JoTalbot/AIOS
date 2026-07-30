
import json
import time
import logging
import re
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from captcha_paid_gate import paid_captcha_slot

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("direct_claim")

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

SKILL_DIR = Path("/root/agents/-Octopus/skills/core/money-earner-orchestrator")
CONFIG = SKILL_DIR / "config" / "faucet_config.json"
DATA = SKILL_DIR / "data"

if __name__ == '__main__' and os.environ.get('OCTOPUS_EXTERNAL_EFFECT_LOCKED') != '1':
    raise SystemExit('paid CAPTCHA executor requires with_external_effect_lock.sh')

def load_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except:
        return default or {}

def solve_hcaptcha_2captcha(sitekey, page_url, api_key):
    """Solve hCaptcha via 2Captcha API."""
    import urllib.request
    import urllib.error

    # Create task
    payload = json.dumps({
        "clientKey": api_key,
        "task": {
            "type": "HCaptchaTaskProxyless",
            "websiteURL": page_url,
            "websiteKey": sitekey
        }
    }).encode()

    req = urllib.request.Request(
        "https://api.2captcha.com/createTask",
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    log.info("Creating 2Captcha task...")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
    except Exception as e:
        log.error(f"createTask failed: {e}")
        return None

    if result.get("errorId", 0) != 0:
        log.error(f"createTask error: {result}")
        return None

    task_id = result.get("taskId")
    if not task_id:
        log.error(f"No taskId: {result}")
        return None

    log.info(f"Task {task_id} created. Polling for result...")

    # Poll for result (max 120 seconds)
    for i in range(40):
        time.sleep(3)
        payload = json.dumps({"clientKey": api_key, "taskId": task_id}).encode()
        req = urllib.request.Request(
            "https://api.2captcha.com/getTaskResult",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
        except Exception as e:
            log.warning(f"getTaskResult error (attempt {i+1}): {e}")
            continue

        status = result.get("status")
        if status == "ready":
            token = result.get("solution", {}).get("gRecaptchaResponse", "")
            if token:
                log.info(f"Solved in ~{(i+1)*3}s, token length={len(token)}")
                return token
            log.error(f"No token in solution: {result}")
            return None

        if result.get("errorId", 0) != 0:
            log.error(f"Task failed: {result}")
            return None

        log.info(f"  ... still processing ({(i+1)*3}s)")

    log.error("Timeout waiting for captcha solution")
    return None


def main():
    config = load_json(CONFIG)
    api_key = config.get("captcha", {}).get("2captcha", {}).get("api_key", "")
    ln_address = config.get("lightning_address", "")

    if not api_key:
        log.error("No 2captcha API key in config!")
        return

    if not ln_address:
        log.error("No lightning_address in config!")
        return

    log.info(f"Lightning Address: {ln_address}")
    log.info(f"2Captcha API key: {api_key[:8]}...")

    # Target faucet
    faucet_url = "https://lightningnetworkstores.com/faucet"
    sitekey = os.environ.get("FAUCET_SITEKEY", "")

    # Step 1: Solve captcha first (before opening browser — saves browser time)
    log.info(f"\n{'='*50}")
    log.info(f"STEP 1: Solving hCaptcha via 2Captcha")
    log.info(f"{'='*50}")

    token = solve_hcaptcha_2captcha(sitekey, faucet_url, api_key)

    if not token:
        log.error("CAPTCHA SOLVING FAILED — aborting")
        return

    log.info(f"Token obtained: {token[:50]}...")

    # Step 2: Open page with Playwright, inject token, click claim
    log.info(f"\n{'='*50}")
    log.info(f"STEP 2: Opening faucet page and injecting token")
    log.info(f"{'='*50}")

    from playwright.sync_api import sync_playwright

    ss_dir = DATA / "screenshots"
    ss_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=UA, viewport={"width": 1280, "height": 900})

            # Navigate
            log.info(f"Navigating to {faucet_url}...")
            page.goto(faucet_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            # Screenshot BEFORE
            ss_before = str(ss_dir / "lns_faucet_before.png")
            page.screenshot(path=ss_before, full_page=True)
            log.info(f"Screenshot BEFORE: {ss_before}")

            # Check what's on the page
            page_text = page.inner_text("body")
            log.info(f"Page text (first 500 chars): {page_text[:500]}")

            # Look for Lightning Address input
            ln_inputs = page.query_selector_all('input')
            for inp in ln_inputs:
                try:
                    placeholder = inp.get_attribute("placeholder") or ""
                    name = inp.get_attribute("name") or ""
                    input_type = inp.get_attribute("type") or ""
                    log.info(f"  Input found: name={name} placeholder={placeholder} type={input_type}")
                    if "@walletofsatoshi" in placeholder.lower() or "lightning" in placeholder.lower() or "lnurl" in placeholder.lower() or "email" in input_type.lower():
                        log.info(f"  -> Filling with Lightning Address: {ln_address}")
                        inp.fill(ln_address)
                except:
                    pass

            # Inject hCaptcha token
            log.info("Injecting hCaptcha token...")
            try:
                page.evaluate("""(token) => {
                    // Set textarea value
                    var ta = document.querySelector('textarea[name="h-captcha-response"]');
                    if (ta) {
                        ta.value = token;
                        ta.textContent = token;
                        ta.dispatchEvent(new Event('change', {bubbles: true}));
                    }

                    // Try hcaptcha.setResponse
                    if (window.hcaptcha) {
                        try { window.hcaptcha.setResponse(token); } catch(e) {}
                    }

                    // SetgetResponse override
                    if (window.hcaptcha) {
                        window.hcaptcha.getResponse = function() { return token; };
                    }

                    return 'token_injected';
                }""", token)
                log.info("Token injected successfully")
            except Exception as e:
                log.error(f"Token injection failed: {e}")

            page.wait_for_timeout(1000)

            # Find and click claim button
            log.info("Looking for claim button...")
            clicked = False
            for selector in [
                'button:has-text("Get Sat")',
                'button:has-text("Claim")',
                'button:has-text("claim")',
                'button:has-text("Get Free")',
                'input[type="submit"]',
                'button[type="submit"]',
            ]:
                try:
                    el = page.query_selector(selector)
                    if el and el.is_visible():
                        btn_text = el.inner_text()
                        log.info(f"Found button '{btn_text}' via {selector}")
                        el.click()
                        clicked = True
                        break
                except:
                    pass

            if not clicked:
                # Try any visible button
                buttons = page.query_selector_all("button")
                for btn in buttons:
                    try:
                        if btn.is_visible():
                            txt = btn.inner_text().strip()
                            if txt and len(txt) < 50:
                                log.info(f"Fallback: clicking button '{txt}'")
                                btn.click()
                                clicked = True
                                break
                    except:
                        pass

            if not clicked:
                log.warning("No claim button found!")

            # Wait for result
            log.info("Waiting 8s for page response...")
            page.wait_for_timeout(8000)

            # Screenshot AFTER
            ss_after = str(ss_dir / "lns_faucet_after.png")
            page.screenshot(path=ss_after, full_page=True)
            log.info(f"Screenshot AFTER: {ss_after}")

            # Analyze result
            page_text_after = page.inner_text("body")
            log.info(f"\nPage text AFTER (first 800 chars):\n{page_text_after[:800]}")

            # Check for LNURL
            html = page.content()
            lnurl_patterns = [
                r'lnurl[wp]?:[a-zA-HJ-NP-Za-km-z1-9]+',
                r'lightning:[a-zA-HJ-NP-Za-km-z1-9]+',
            ]
            for pattern in lnurl_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    log.info(f"\n*** LNURL FOUND: {matches[0][:80]}... ***")

            # Check for success/error messages
            if "payment" in page_text_after.lower() or "sent" in page_text_after.lower():
                log.info("*** POSSIBLE SUCCESS: payment/sent keywords found ***")
            if "error" in page_text_after.lower():
                log.info(f"*** ERROR keyword found in page ***")

            # Check URL changes
            current_url = page.url
            if current_url != faucet_url:
                log.info(f"*** URL changed to: {current_url} ***")

            # Wait more and check again
            log.info("Waiting another 5s...")
            page.wait_for_timeout(5000)
            page_text_final = page.inner_text("body")
            if page_text_final != page_text_after:
                log.info(f"\nPage text FINAL (first 500 chars):\n{page_text_final[:500]}")

            # Third screenshot
            ss_final = str(ss_dir / "lns_faucet_final.png")
            page.screenshot(path=ss_final, full_page=True)
            log.info(f"Screenshot FINAL: {ss_final}")

        finally:
            browser.close()

    log.info("\nDone!")


if __name__ == "__main__":
    main()
