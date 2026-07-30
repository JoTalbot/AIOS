#!/usr/bin/env python3
"""lightningfaucet_claimer.py — LightningFaucet.com faucet claimer.

LightningFaucet is a SPA with:
  - "Free Spin" wheel faucet (claim sats weekly)
  - Account-based (session cookies + CSRF)
  - WebSocket for live balance updates
  - LNURL-auth or email/password login

Strategy:
  1. Use Playwright to navigate to the Free Spin page
  2. Wait for spin button, click it
  3. Wait for result, extract sats won
  4. Optionally use `lw` CLI for balance/withdraw

The lf_ API key is for the MCP operator wallet system (balance, payments).
The faucet "Free Spin" requires a website session.

Usage:
  python3 lightningfaucet_claimer.py --spin           # Do one free spin
  python3 lightningfaucet_claimer.py --balance         # Check wallet balance via lw CLI
  python3 lightningfaucet_claimer.py --spin --loop     # Loop with cooldown
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERROR: playwright not installed")
    sys.exit(1)

# ─── Paths ───────────────────────────────────────────────
SKILL_DIR = Path(os.environ.get("OCTOPUS_ME_SKILL_DIR") or Path(__file__).resolve().parents[1])
CONFIG = SKILL_DIR / "config"
DATA = SKILL_DIR / "data"
FAUCET_CFG = CONFIG / "faucet_config.json"
LEDGER = DATA / "faucet_ledger.json"
COOLDOWN_FILE = DATA / "faucet_cooldowns.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("lightningfaucet")

BASE_URL = "https://lightningfaucet.com"
FREE_SPIN_URL = f"{BASE_URL}/casino/spin"


def load_json(path: Path, default: Any = None) -> Any:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if default is not None and isinstance(default, dict):
            if not isinstance(data, dict):
                return default
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            return data
        return data
    except Exception:
        return default if default is not None else {}


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_ledger(faucet_id: str, coin: str, amount: str, status: str, details: str = ""):
    try:
        ledger = load_json(LEDGER, {"claims": []})
        if "claims" not in ledger:
            ledger["claims"] = []
        entry = {
            "ts": utc_now(),
            "faucet_id": faucet_id,
            "coin": coin,
            "amount": amount,
            "status": status,
            "details": details,
        }
        ledger["claims"].append(entry)
        ledger["claims"] = ledger["claims"][-500:]
        save_json(LEDGER, ledger)
    except Exception as e:
        log.warning(f"Ledger append failed: {e}")


def lw_cli(args: list, timeout: int = 30) -> Dict[str, Any]:
    """Run the `lw` CLI tool and return parsed JSON output."""
    try:
        result = subprocess.run(
            ["lw"] + args,
            capture_output=True, text=True, timeout=timeout,
        )
        output = result.stdout.strip()
        if output:
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return {"raw": output, "exit_code": result.returncode}
        return {"error": result.stderr.strip(), "exit_code": result.returncode}
    except subprocess.TimeoutExpired:
        return {"error": f"timeout ({timeout}s)"}
    except FileNotFoundError:
        return {"error": "lw CLI not installed (npm install -g lightning-wallet-mcp)"}
    except Exception as e:
        return {"error": str(e)}


def check_balance_cli(api_key: str) -> Dict[str, Any]:
    """Check wallet balance using the lw CLI."""
    env = {**os.environ, "LIGHTNING_WALLET_API_KEY": api_key}
    try:
        result = subprocess.run(
            ["lw", "balance"],
            capture_output=True, text=True, timeout=15,
            env=env,
        )
        output = result.stdout.strip()
        if output:
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                pass
        return {"error": result.stderr.strip() or "no output"}
    except Exception as e:
        return {"error": str(e)}


def do_free_spin(headless: bool = True) -> Dict[str, Any]:
    """Navigate to LightningFaucet Free Spin page and attempt to spin."""
    result = {
        "faucet_id": "lightningfaucet-spin",
        "coin": "BTC",
        "url": FREE_SPIN_URL,
        "status": "unknown",
        "amount": "0",
        "message": "",
        "timestamp": utc_now(),
    }

    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            log.info(f"Loading {FREE_SPIN_URL}...")
            page.goto(FREE_SPIN_URL, wait_until="commit", timeout=30000)
            time.sleep(3)

            # Wait for page to load
            try:
                page.wait_for_load_state("domcontentloaded", timeout=15000)
            except PlaywrightTimeout:
                log.warning("DOM load timeout, continuing...")

            time.sleep(2)
            html = page.content()

            # Check if we need to login
            page_text = page.inner_text("body") if page.query_selector("body") else ""

            if any(kw in page_text.lower() for kw in ["sign in", "log in", "login", "create account", "register"]):
                result["status"] = "need_login"
                result["message"] = "Login required — LightningFaucet needs a session (LNURL-auth or email/password)"
                log.warning("Login required for LightningFaucet")
                browser.close()
                return result

            # Check if we're on the spin page
            if "spin" not in page_text.lower() and "free" not in page_text.lower():
                # Maybe redirected to home
                log.info(f"Page text excerpt: {page_text[:300]}")

            # Look for spin button or free spin button
            spin_selectors = [
                'button:has-text("Spin")',
                'button:has-text("Free Spin")',
                'button:has-text("Claim")',
                'button[data-action="spin"]',
                'button.spin-button',
                '.spin-btn',
                '#spin-button',
                'button.btn-spin',
                'a:has-text("Spin")',
            ]

            clicked = False
            for sel in spin_selectors:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        txt = el.inner_text().strip()[:60]
                        log.info(f"Found spin button: '{txt}' via {sel}")
                        el.click()
                        clicked = True
                        break
                except Exception:
                    continue

            if not clicked:
                # Try to find any button that could be the spin
                try:
                    buttons = page.query_selector_all("button")
                    for btn in buttons:
                        try:
                            if btn.is_visible():
                                txt = (btn.inner_text() or "").strip().lower()
                                if any(kw in txt for kw in ["spin", "free", "claim", "play"]):
                                    log.info(f"Found button: '{btn.inner_text().strip()[:60]}'")
                                    btn.click()
                                    clicked = True
                                    break
                        except Exception:
                            continue
                except Exception:
                    pass

            if not clicked:
                # Save HTML for debugging
                try:
                    debug_path = f"/tmp/lightningfaucet_{int(time.time())}.html"
                    with open(debug_path, "w") as f:
                        f.write(html)
                    log.info(f"HTML saved: {debug_path}")
                    page.screenshot(path=f"/tmp/lightningfaucet_{int(time.time())}.png", full_page=True)
                except Exception:
                    pass

                result["status"] = "no_button"
                result["message"] = "No spin button found"
                log.warning("No spin button found")
                browser.close()
                return result

            # Wait for spin result
            log.info("Waiting for spin result...")
            time.sleep(5)

            # Try waiting for result text
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except PlaywrightTimeout:
                pass

            time.sleep(3)

            # Check for result
            post_text = page.inner_text("body") if page.query_selector("body") else ""
            post_html = page.content()

            # Look for sats amount in result
            sats_patterns = [
                r'(\d+)\s*sats?',
                r'won\s+(\d+)',
                r'you\s+(?:got|won|received)\s+(\d+)',
                r'congratulations.*?(\d+)',
                r'reward.*?(\d+)',
            ]
            amount_found = ""
            for pat in sats_patterns:
                try:
                    m = re.search(pat, post_text, re.IGNORECASE)
                    if m:
                        amount_found = m.group(1)
                        break
                except Exception:
                    continue

            # Check for success/error keywords
            combined = post_text.lower()
            if any(kw in combined for kw in ["congratulations", "you won", "you got", "sats added", "reward"]):
                result["status"] = "claimed"
                result["amount"] = f"{amount_found} sats" if amount_found else "unknown"
                result["message"] = f"Won {amount_found} sats" if amount_found else "Spin successful"
                log.info(f"CLAIMED! {result['message']}")
            elif any(kw in combined for kw in ["cooldown", "wait", "already", "try again", "come back"]):
                result["status"] = "cooldown"
                result["message"] = "On cooldown"
                log.info("On cooldown")
            else:
                result["status"] = "spun_unknown"
                result["message"] = "Spun but result unclear"
                log.info("Spun, unclear result")

            # Save post-spin state
            try:
                page.screenshot(path=f"/tmp/lightningfaucet_spin_{int(time.time())}.png", full_page=True)
            except Exception:
                pass

            browser.close()
            browser = None

    except PlaywrightTimeout:
        result["status"] = "timeout"
        result["message"] = "Page load timeout"
        log.error("Timeout")
    except Exception as e:
        result["status"] = "exception"
        result["message"] = str(e)[:300]
        log.error(f"Exception: {e}")
    finally:
        try:
            if browser:
                browser.close()
        except Exception:
            pass

    # Log to ledger
    append_ledger(
        faucet_id="lightningfaucet-spin",
        coin="BTC",
        amount=result.get("amount", "0"),
        status=result["status"],
        details=result.get("message", ""),
    )

    return result


def main():
    parser = argparse.ArgumentParser(description="LightningFaucet.com Claimer")
    parser.add_argument("--spin", action="store_true", help="Do a free spin")
    parser.add_argument("--balance", action="store_true", help="Check wallet balance (lw CLI)")
    parser.add_argument("--whoami", action="store_true", help="Show operator identity")
    parser.add_argument("--loop", action="store_true", help="Loop mode (spin only)")
    parser.add_argument("--interval", type=int, default=3600, help="Loop interval in seconds (default: 3600 = 1h)")
    parser.add_argument("--headed", action="store_true", help="Visible browser")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    # Load config for API key
    cfg = load_json(FAUCET_CFG, {})
    api_key = cfg.get("lightningfaucet", {}).get("api_key", "")

    if not args.spin and not args.balance and not args.whoami:
        parser.print_help()
        print("\nDefault: --spin --balance")
        args.spin = True
        args.balance = True

    results = {}

    if args.whoami:
        env = {**os.environ, "LIGHTNING_WALLET_API_KEY": api_key}
        try:
            result = subprocess.run(
                ["lw", "whoami"], capture_output=True, text=True, timeout=15, env=env,
            )
            print(result.stdout.strip())
            results["whoami"] = json.loads(result.stdout.strip()) if result.stdout.strip() else {"error": "no output"}
        except Exception as e:
            print(f"Error: {e}")
            results["whoami"] = {"error": str(e)}

    if args.balance:
        if not api_key:
            log.error("No LightningFaucet API key in config")
            bal = {"error": "no API key"}
        else:
            bal = check_balance_cli(api_key)
        print(f"Balance: {bal}")
        results["balance"] = bal

    if args.spin:
        iteration = 0
        while True:
            iteration += 1
            log.info(f"{'='*50} SPIN ITERATION #{iteration} {'='*50}")

            spin_result = do_free_spin(headless=not args.headed)
            results["spin"] = spin_result

            if args.json:
                print(json.dumps(spin_result, indent=2))
            else:
                print(f"\n{'='*60}")
                print(f"LIGHTNINGFAUCET SPIN RESULT")
                print(f"{'='*60}")
                print(f"  Status:  {spin_result['status']}")
                print(f"  Amount:  {spin_result.get('amount', '0')}")
                print(f"  Message: {spin_result.get('message', '')}")
                print(f"{'='*60}\n")

            if not args.loop:
                break

            log.info(f"Sleeping {args.interval}s...")
            time.sleep(args.interval)

    return 0 if all(r.get("status") != "error" for r in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())