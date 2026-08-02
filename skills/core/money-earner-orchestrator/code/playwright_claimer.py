#!/usr/bin/env python3
"""playwright_claimer.py — Playwright-based клеймер для кранов с капчами.

Поддерживаемые стратегии:
  1. DogeFaucet: reCAPTCHA через 2Captcha → инжект токена → заполнить адрес → submit
  2. Stakely: Turnstile (auto в браузере) → заполнить адрес → submit (Nuxt-рендер)

Запуск:
  python3 playwright_claimer.py --faucet dogefaucet
  python3 playwright_claimer.py --faucet stakely-polygon
  python3 playwright_claimer.py --all
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from captcha_paid_gate import paid_captcha_slot
from captcha_budget_atomic import atomic_record_spend
from typing import Any, Dict, Optional

# Playwright
from playwright.async_api import async_playwright

SKILL_DIR = Path(os.environ.get("OCTOPUS_ME_SKILL_DIR") or Path(__file__).resolve().parents[1])
CONFIG = SKILL_DIR / "config"
DATA = SKILL_DIR / "data"
FAUCET_CFG = CONFIG / "faucet_config.json"
LEDGER = DATA / "faucet_ledger.json"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("pw_claimer")


if __name__ == '__main__' and os.environ.get('OCTOPUS_EXTERNAL_EFFECT_LOCKED') != '1':
    raise SystemExit('paid CAPTCHA executor requires with_external_effect_lock.sh')

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default or {}


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def solve_recaptcha_2captcha(api_key: str, sitekey: str, url: str) -> Optional[str]:
    """Solve reCAPTCHA v2 via 2Captcha HTTP API."""
    payload = json.dumps({
        "clientKey": api_key,
        "task": {"type": "RecaptchaV2TaskProxyless", "websiteURL": url, "websiteKey": sitekey},
    }).encode()
    req = urllib.request.Request("https://api.2captcha.com/createTask", data=payload,
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode()
    if not isinstance(raw, str) or not raw.strip():
        log.error(f"Empty response from 2Captcha")
        return None
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        log.error(f"Non-JSON response: {raw[:200]}")
        return None
    if not isinstance(result, dict):
        log.error(f"Non-dict response: {type(result)}")
        return None
    task_id = str(result.get("taskId", ""))
    if not task_id or task_id == "None" or result.get("errorId", 0) != 0:
        log.error(f"createTask failed: {result.get('errorDescription', '?')}")
        return None
    log.info(f"reCAPTCHA task {task_id[:12]}... created")
    for i in range(60):
        time.sleep(3)
        payload = json.dumps({"clientKey": api_key, "taskId": task_id}).encode()
        req = urllib.request.Request("https://api.2captcha.com/getTaskResult", data=payload,
                                    headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
        try:
            result = json.loads(raw)
        except Exception:
            continue
        if not isinstance(result, dict):
            continue
        if result.get("status") == "ready":
            token = result.get("solution", {}).get("gRecaptchaResponse", "")
            if token:
                log.info(f"reCAPTCHA solved in ~{(i+1)*3}s")
                return token
        if result.get("errorId", 0) != 0:
            return None
    return None


def solve_hcaptcha_2captcha(api_key: str, sitekey: str, url: str) -> Optional[str]:
    """Solve hCaptcha via 2Captcha HTTP API."""
    payload = json.dumps({
        "clientKey": api_key,
        "task": {"type": "HCaptchaTaskProxyless", "websiteURL": url, "websiteKey": sitekey},
    }).encode()
    req = urllib.request.Request("https://api.2captcha.com/createTask", data=payload,
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode()
    if not isinstance(raw, str) or not raw.strip():
        log.error(f"Empty response from 2Captcha")
        return None
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        log.error(f"Non-JSON response: {raw[:200]}")
        return None
    if not isinstance(result, dict):
        log.error(f"Non-dict response: {type(result)}")
        return None
    task_id = str(result.get("taskId", ""))
    if not task_id or task_id == "None" or result.get("errorId", 0) != 0:
        log.error(f"createTask failed: {result.get('errorDescription', '?')}")
        return None
    log.info(f"hCaptcha task {task_id[:12]}... created")
    for i in range(60):
        time.sleep(3)
        payload = json.dumps({"clientKey": api_key, "taskId": task_id}).encode()
        req = urllib.request.Request("https://api.2captcha.com/getTaskResult", data=payload,
                                    headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
        try:
            result = json.loads(raw)
        except Exception:
            continue
        if not isinstance(result, dict):
            continue
        if result.get("status") == "ready":
            token = result.get("solution", {}).get("gRecaptchaResponse", "")
            if token:
                log.info(f"hCaptcha solved in ~{(i+1)*3}s")
                return token
        if result.get("errorId", 0) != 0:
            return None
    return None


def record_spend(cost_usd: float) -> None:
    atomic_record_spend(DATA / 'daily_captcha_budget.json', cost_usd, source='playwright_claimer.py')

async def claim_dogefaucet(page, api_key: str) -> Dict[str, Any]:
    """Claim from dogefaucet.com using reCAPTCHA solve + form submit."""
    url = "https://www.dogefaucet.com"
    sitekey = os.environ.get("FAUCET_SITEKEY", "")

    # Step 1: Navigate
    log.info("[dogefaucet] Navigating...")
    await page.goto(url, timeout=15000, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    # Step 2: Find address input (name="key" on dogefaucet)
    addr_input = await page.query_selector('input[name="key"], input[name="address"]')
    if not addr_input:
        for inp in await page.query_selector_all("input[type='text'], input:not([type])"):
            n = await inp.get_attribute("name") or ""
            if n in ("key", "address", "wallet_address"):
                addr_input = inp
                break
    if not addr_input:
        return {"status": "error", "message": "No address input found"}
    log.info(f"[dogefaucet] Found input: name={await addr_input.get_attribute('name')}")

    # Step 3: Solve reCAPTCHA
    log.info("[dogefaucet] Solving reCAPTCHA...")
    token = solve_recaptcha_2captcha(api_key, sitekey, url)
    if not token:
        return {"status": "error", "message": "reCAPTCHA solve failed"}
    record_spend(0.002)
    log.info(f"[dogefaucet] Token len={len(token)}")

    # Step 4: Fill configured production DOGE address.
    cfg = load_json(CONFIG / "faucet_config.json", {})
    doge_address = str(cfg.get("doge_wallet", "")).strip()
    if not re.fullmatch(r"D[1-9A-HJ-NP-Za-km-z]{24,34}", doge_address):
        return {"status": "error", "message": "Valid configured DOGE address required"}
    await addr_input.fill(doge_address)
    log.info(f"[dogefaucet] Filled configured DOGE address: {doge_address[:8]}...{doge_address[-6:]}")
    await page.wait_for_timeout(300)

    # Step 5: Inject reCAPTCHA token
    log.info("[dogefaucet] Injecting token...")
    safe_token = token.replace("'", "\\'")
    await page.evaluate(f"""
        (function() {{
            var ta = document.getElementById('g-recaptcha-response');
            if (!ta) {{
                ta = document.createElement('textarea');
                ta.name = 'g-recaptcha-response';
                ta.id = 'g-recaptcha-response';
                ta.style.display = 'none';
                document.forms[0].appendChild(ta);
            }}
            ta.value = '{safe_token}'; // FIXED XSS: was innerHTML, now value
            ta.value = '{safe_token}';
        }})();
    """)
    await page.wait_for_timeout(300)

    # Step 6: Submit
    log.info("[dogefaucet] Submitting...")
    submit_btn = await page.query_selector('button[type="submit"], input[type="submit"], button:has-text("Claim"), button:has-text("Get"), button:has-text("Send")')
    if submit_btn:
        await submit_btn.click()
    else:
        form = await page.query_selector("form")
        if form:
            await form.evaluate("f => f.submit()")
    await page.wait_for_timeout(5000)

    # Step 7: Screenshot + check result
    await page.screenshot(path=str(DATA / "screenshots" / "dogefaucet_claim.png"))
    url_after = page.url
    html = await page.content()
    low = html.lower()
    log.info(f"[dogefaucet] After: url={url_after}")

    msgs = []
    for el in await page.query_selector_all('.alert, .message, .result, .notice, [class*="success"], [class*="error"]'):
        txt = (await el.inner_text()).strip()[:200]
        if txt: msgs.append(txt)

    result = {"faucet": "dogefaucet", "coin": "DOGE", "ts": utc_now(), "url_after": url_after, "messages": msgs[:5]}
    visible = " ".join(msgs).lower()
    error_terms = ["error", "invalid", "doesn't validate", "does not validate", "failed", "wrong", "already", "limit", "sorry"]
    success_terms = ["successfully sent", "payout sent", "claim successful", "doge sent", "have been added to your balance"]
    if any(x in visible for x in error_terms):
        result["status"] = "fail"
    elif any(x in visible for x in success_terms):
        result["status"] = "success"
    else:
        result["status"] = "unknown"
    return result


# ============================================================
# STRATEGY: Stakely — Turnstile auto + form submit
# ============================================================
async def claim_stakely(page, coin: str = "polygon") -> Dict[str, Any]:
    """Claim from stakely.io using Turnstile (auto-solved in browser)."""
    paths = {
        "polygon": "https://stakely.io/faucet/polygon-pol",
        "multi": "https://stakely.io/faucet",
    }
    url = paths.get(coin, paths["multi"])
    log.info(f"[stakely-{coin}] Navigating to {url}...")

    # Capture API calls
    api_calls = []
    def on_resp(response):
        if "api.stakely" in response.url:
            api_calls.append({"url": response.url, "status": response.status, "body": ""})
    page.on("response", on_resp)

    await page.goto(url, timeout=15000, wait_until="domcontentloaded")
    await page.wait_for_timeout(4000)

    # Find address input (first empty text input)
    address = ""
    all_inputs = await page.query_selector_all("input")
    for inp in all_inputs:
        itype = await inp.get_attribute("type") or "text"
        name = await inp.get_attribute("name") or ""
        if itype in ("text", "", None) and not name:
            # This is likely the address field (no name = Nuxt/Vue component)
            # We need a real wallet address for this chain
            if coin == "polygon":
                address = "0x0000000000000000000000000000000000000001"
            await inp.fill(address)
            log.info(f"[stakely-{coin}] Filled address: {address}")
            break

    # Wait for Turnstile to complete
    log.info("[stakely] Waiting for Turnstile...")
    await page.wait_for_timeout(3000)

    # Check Turnstile response
    ts_token = await page.evaluate("document.querySelector('input[name=cf-turnstile-response]')?.value || ''")
    if ts_token:
        log.info(f"[stakely] Turnstile solved: token len={len(ts_token)}")
    else:
        log.warning("[stakely] No Turnstile token")

    # Click Submit
    submit = await page.query_selector("button:has-text('Submit'), button[type=submit]")
    if submit:
        # Capture response after click
        async with page.expect_response(lambda r: "api.stakely" in r.url, timeout=10000) as resp_info:
            await submit.click()
            try:
                resp = await resp_info.value
                body = await resp.text()
                log.info(f"[stakely] API response: {resp.status} {body[:200]}")
            except Exception:
                pass
        await page.wait_for_timeout(2000)
    else:
        log.error("[stakely] No submit button found")

    return {"faucet": f"stakely-{coin}", "coin": coin.upper(), "ts": utc_now(),
            "status": "attempted", "turnstile": bool(ts_token), "api_calls": len(api_calls)}


# ============================================================
# MAIN
# ============================================================
async def run_all(api_key: str, selected: str = "all") -> Dict[str, Any]:
    """Run selected Playwright-based claims sequentially."""
    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=UA)

        if selected in ("all", "dogefaucet"):
            log.info("=" * 50)
            log.info("Claiming DogeFaucet (DOGE)...")
            log.info("=" * 50)
            page = await context.new_page()
            try:
                results["dogefaucet"] = await claim_dogefaucet(page, api_key)
            except Exception as e:
                results["dogefaucet"] = {"status": "error", "message": str(e)}
            log.info(f"Result: {results.get('dogefaucet', {})}")
            await page.close()

        if selected in ("all", "stakely-polygon"):
            log.info("=" * 50)
            log.info("Claiming Stakely (POL)...")
            log.info("=" * 50)
            page = await context.new_page()
            try:
                results["stakely-polygon"] = await claim_stakely(page, "polygon")
            except Exception as e:
                results["stakely-polygon"] = {"status": "error", "message": str(e)}
            log.info(f"Result: {results.get('stakely-polygon', {})}")
            await page.close()

        await browser.close()

    return results


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Playwright faucet claimer")
    ap.add_argument("--faucet", type=str, default="all", help="dogefaucet, stakely-polygon, all")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    config = load_json(FAUCET_CFG, {})
    api_key = config.get("captcha", {}).get("2captcha", {}).get("api_key", "")
    if not api_key:
        log.error("No 2Captcha API key!")
        return 1

    results = asyncio.run(run_all(api_key, args.faucet))

    # Save to ledger
    ledger = load_json(LEDGER, {"vector": "САМООБЕСПЕЧЕНИЕ", "runs": [], "total_sats_claimed": 0})
    entry = {
        "ts": utc_now(),
        "mode": "playwright_claimer",
        "vector": "САМООБЕСПЕЧЕНИЕ",
        "claims": results,
    }
    ledger["runs"].append(entry)
    ledger["updated"] = utc_now()
    save_json(LEDGER, ledger)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for fid, r in results.items():
            st = r.get("status", "?")
            msg = r.get("message", "")[:80]
            log.info(f"  {fid}: {st} — {msg}")


if __name__ == "__main__":
    raise SystemExit(main())
