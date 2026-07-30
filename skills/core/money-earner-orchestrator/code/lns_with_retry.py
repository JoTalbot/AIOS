#!/usr/bin/env python3
"""lns_with_retry.py — LNS BTC faucet with auto-retry and circuit breaker.

Enhanced version of faucet_one_shot.py with:
  - Up to 3 retries with exponential backoff on HTTP 500
  - Consecutive failure tracking
  - Circuit breaker (skip LNS after N consecutive 500s)
  - Health status persistence across runs

Usage:
  python3 lns_with_retry.py
  python3 lns_with_retry.py --max-retries 5
  python3 lns_with_retry.py --json

Cost: ~$0.002 per captcha solve via 2Captcha.
Vector: САМООБЕСПЕЧЕНИЕ (L0 zero-cost optional).
"""

import argparse
import hashlib
import json
import logging
import os
import random
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from captcha_budget_atomic import atomic_record_spend, atomic_try_reserve
from typing import Any, Dict, Optional

SKILL_DIR = Path(os.environ.get("OCTOPUS_ME_SKILL_DIR") or Path(__file__).resolve().parents[1])
CONFIG = SKILL_DIR / "config"
DATA = SKILL_DIR / "data"
FAUCET_CFG = CONFIG / "faucet_config.json"
LEDGER = DATA / "faucet_ledger.json"
HEALTH_FILE = DATA / "lns_health.json"
BUDGET_FILE = DATA / "daily_captcha_budget.json"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
BASE_URL = "https://lightningnetworkstores.com"
SITEKEY = os.environ.get("LNS_SITEKEY", "")

# Retry / circuit breaker defaults
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_DELAY = 60        # seconds
CIRCUIT_BREAKER_THRESHOLD = 5       # consecutive 500s before breaker opens
CIRCUIT_BREAKER_COOLDOWN = 1800     # seconds (30 min) before retrying after breaker opens

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("lns_retry")


# ─── Helpers ─────────────────────────────────────────────

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if default is not None and isinstance(default, dict):
            if not isinstance(data, dict):
                return default.copy()
            merged = default.copy()
            merged.update(data)
            return merged
        return data
    except Exception:
        return default.copy() if default is not None else {}


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_config() -> Dict[str, Any]:
    return load_json(FAUCET_CFG, {})


def check_budget(cfg: Dict[str, Any]) -> bool:
    captcha = cfg.get("captcha", {})
    if not captcha.get("auto_paid_enabled", False):
        log.warning("Paid CAPTCHA disabled by config")
        return False
    max_daily = captcha.get("max_daily_budget_usd", 0.50)
    budget = load_json(BUDGET_FILE, {"date": "", "spent_usd": 0.0, "solves": 0})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if budget.get("date") != today:
        budget = {"date": today, "spent_usd": 0.0, "solves": 0}
        save_json(BUDGET_FILE, budget)
    return budget["spent_usd"] < max_daily


def record_spend(cost_usd: float) -> None:
    atomic_record_spend(BUDGET_FILE, cost_usd, source='lns_with_retry.py')

def load_health() -> Dict[str, Any]:
    return load_json(HEALTH_FILE, {
        "consecutive_5xx": 0,
        "circuit_breaker_open": False,
        "circuit_breaker_opened_at": None,
        "last_success": None,
        "last_5xx": None,
        "total_attempts": 0,
        "total_successes": 0,
        "total_5xx_errors": 0,
        "total_captcha_solved": 0,
        "total_captcha_cost_usd": 0.0,
    })


def save_health(health: Dict[str, Any]) -> None:
    health["updated"] = utc_now()
    save_json(HEALTH_FILE, health)


def is_circuit_breaker_open(health: Dict[str, Any]) -> bool:
    """Check if circuit breaker is open and should remain open."""
    if not health.get("circuit_breaker_open"):
        return False

    opened_at = health.get("circuit_breaker_opened_at")
    if not opened_at:
        return False

    try:
        opened_time = datetime.fromisoformat(opened_at)
        elapsed = (datetime.now(timezone.utc) - opened_time).total_seconds()
        if elapsed > CIRCUIT_BREAKER_COOLDOWN:
            # Cooldown passed, reset breaker
            log.info(f"Circuit breaker cooldown elapsed ({elapsed:.0f}s > {CIRCUIT_BREAKER_COOLDOWN}s), resetting")
            health["circuit_breaker_open"] = False
            health["consecutive_5xx"] = 0
            health["circuit_breaker_opened_at"] = None
            save_health(health)
            return False
    except (ValueError, TypeError):
        pass

    return True


# ─── 2Captcha hCaptcha Solver ───────────────────────────

def solve_hcaptcha(api_key: str) -> Optional[str]:
    log.info("Solving hCaptcha via 2Captcha...")
    payload = json.dumps({
        "clientKey": api_key,
        "task": {
            "type": "HCaptchaTaskProxyless",
            "websiteURL": f"{BASE_URL}/faucet",
            "websiteKey": SITEKEY,
        },
    }).encode()

    try:
        req = urllib.request.Request(
            "https://api.2captcha.com/createTask",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
    except Exception as e:
        log.error(f"2Captcha createTask error: {e}")
        return None

    if result.get("errorId", 0) != 0:
        log.error(f"2Captcha error: {result.get('errorDescription', result)}")
        return None

    task_id = result.get("taskId")
    if not task_id:
        log.error("2Captcha: no taskId")
        return None

    log.info(f"Task {str(task_id)[:12]}... created, waiting...")

    for i in range(40):
        time.sleep(3)
        try:
            payload = json.dumps({"clientKey": api_key, "taskId": task_id}).encode()
            req = urllib.request.Request(
                "https://api.2captcha.com/getTaskResult",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
        except Exception as e:
            log.warning(f"Poll error ({(i+1)*3}s): {e}")
            continue

        if result.get("status") == "ready":
            token = result.get("solution", {}).get("gRecaptchaResponse", "")
            if token:
                log.info(f"Captcha solved in ~{(i+1)*3}s (token {len(token)} chars)")
                return token

        if result.get("errorId", 0) != 0:
            log.error(f"2Captcha task failed: {result.get('errorDescription', '?')}")
            return None

        if (i + 1) % 10 == 0:
            log.info(f"  waiting... {(i+1)*3}s")

    log.error("Captcha solve timeout (120s)")
    return None


# ─── LNS Claim API ──────────────────────────────────────

def claim_lnurl1(token: str) -> Dict[str, Any]:
    bfg = hashlib.md5(str(random.random()).encode()).hexdigest()[:32]
    dfg = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:32]
    wfg = "1920x1080"

    params = urllib.parse.urlencode({
        "bfg": bfg, "dfg": dfg, "wfg": wfg,
        "h-captcha-response": token,
        "g-recaptcha-response": "",
    })

    url = f"{BASE_URL}/api/lnurl1?{params}"
    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
        "Referer": f"{BASE_URL}/faucet",
        "Origin": BASE_URL,
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return {"http_status": e.code, "status": "fail", "message": body[:500]}
    except Exception as e:
        return {"http_status": 0, "status": "error", "message": str(e)}

    try:
        j = json.loads(data)
        return {"http_status": status, **j}
    except Exception:
        return {"http_status": status, "status": "unknown", "raw": data[:500]}


# ─── Ledger ─────────────────────────────────────────────

def update_ledger(result: Dict, solve_time_s: float, cost_usd: float, retry_num: int = 0):
    ledger = load_json(LEDGER, {"vector": "САМООБЕСПЕЧЕНИЕ", "runs": [], "total_sats_claimed": 0})
    if not isinstance(ledger, dict):
        ledger = {"vector": "САМООБЕСПЕЧЕНИЕ", "runs": [], "total_sats_claimed": 0}

    success = result.get("status") == "success"
    claim_data = result.get("data", {})
    amount = claim_data.get("amount", 0)

    entry = {
        "ts": utc_now(),
        "faucet": "lightningnetworkstores.com",
        "method": "lns_with_retry",
        "captcha_solver": "2captcha",
        "captcha_solve_time_s": round(solve_time_s, 1),
        "cost_usd": cost_usd,
        "retry_num": retry_num,
        "api_status": result.get("http_status"),
        "success": success,
        "amount_sats": amount,
        "error": result.get("message") if not success else None,
    }

    if success and amount:
        ledger["total_sats_claimed"] = ledger.get("total_sats_claimed", 0) + amount

    if "runs" not in ledger:
        ledger["runs"] = []
    ledger["runs"].append(entry)
    ledger["updated"] = utc_now()
    save_json(LEDGER, ledger)


# ─── Main with Retry Logic ─────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="LNS BTC faucet with auto-retry")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES,
                        help=f"Max retries per attempt (default: {DEFAULT_MAX_RETRIES})")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--force", action="store_true", help="Ignore circuit breaker")
    args = parser.parse_args()

    config = load_config()
    api_key = config.get("captcha", {}).get("2captcha", {}).get("api_key", "")

    if not api_key:
        log.error("2Captcha API key not configured")
        return 1

    if not check_budget(config):
        log.error("Daily budget exhausted or paid CAPTCHA disabled")
        return 1
    max_daily = float(config.get('captcha', {}).get('max_daily_budget_usd', 0.5))
    cost_usd = float(config.get('captcha', {}).get('max_cost_per_solve_usd', 0.003))
    reserved, _ = atomic_try_reserve(BUDGET_FILE, cost_usd, max_daily, source='lns_with_retry.py')
    if not reserved:
        log.error("Daily CAPTCHA budget reservation rejected")
        return 1

    # Load health status
    health = load_health()

    # Check circuit breaker
    if not args.force and is_circuit_breaker_open(health):
        opened_at = health.get("circuit_breaker_opened_at", "?")
        log.warning(f"Circuit breaker is OPEN (since {opened_at})")
        log.warning(f"LNS backend has been returning 500 consistently")
        log.warning(f"Will auto-retry after {CIRCUIT_BREAKER_COOLDOWN}s cooldown")
        log.info("Use --force to override circuit breaker")
        return 2  # special exit code for "circuit breaker open"

    # Solve captcha ONCE, reuse token for all retries
    t0 = time.time()
    token = solve_hcaptcha(api_key)
    solve_time = time.time() - t0

    if not token:
        log.error("Failed to solve captcha")
        return 1

    health["total_captcha_solved"] = health.get("total_captcha_solved", 0) + 1
    health["total_captcha_cost_usd"] = round(
        health.get("total_captcha_cost_usd", 0) + cost_usd, 4
    )

    # Attempt claim with retries
    last_result = None
    for attempt in range(args.max_retries + 1):
        health["total_attempts"] = health.get("total_attempts", 0) + 1
        attempt_label = f" (attempt {attempt + 1}/{args.max_retries + 1})" if attempt > 0 else ""

        log.info(f"Claiming LNS BTC{attempt_label}...")
        result = claim_lnurl1(token)
        last_result = result
        http_status = result.get("http_status", 0)

        if result.get("status") == "success":
            # SUCCESS
            health["total_successes"] = health.get("total_successes", 0) + 1
            health["consecutive_5xx"] = 0
            health["last_success"] = utc_now()
            save_health(health)
            update_ledger(result, solve_time, cost_usd, retry_num=attempt)

            claim = result.get("data", {})
            log.info(f"CLAIMED! {claim.get('amount')} sats")
            log.info(f"Payment request: {claim.get('payment_request', '')[:80]}...")

            if args.json:
                print(json.dumps({
                    "ts": utc_now(),
                    "faucet": "lightningnetworkstores.com",
                    "captcha_solve_time_s": round(solve_time, 1),
                    "cost_usd": cost_usd,
                    "attempt": attempt + 1,
                    "claim_result": result,
                }, indent=2))
            return 0

        elif http_status == 500:
            # Backend error — retryable
            health["consecutive_5xx"] = health.get("consecutive_5xx", 0) + 1
            health["total_5xx_errors"] = health.get("total_5xx_errors", 0) + 1
            health["last_5xx"] = utc_now()

            if attempt < args.max_retries:
                delay = DEFAULT_RETRY_BASE_DELAY * (2 ** attempt)
                log.warning(f"HTTP 500 — backend error, retrying in {delay}s...")
                save_health(health)
                update_ledger(result, solve_time, cost_usd, retry_num=attempt)
                time.sleep(delay)
                continue
            else:
                log.warning(f"HTTP 500 — all {args.max_retries + 1} attempts failed")

                # Check if circuit breaker should open
                if health["consecutive_5xx"] >= CIRCUIT_BREAKER_THRESHOLD:
                    health["circuit_breaker_open"] = True
                    health["circuit_breaker_opened_at"] = utc_now()
                    log.warning(f"Circuit breaker OPENED after {health['consecutive_5xx']} consecutive 500s")
                    log.warning(f"Will skip LNS for {CIRCUIT_BREAKER_COOLDOWN}s ({CIRCUIT_BREAKER_COOLDOWN/60:.0f} min)")

        else:
            # Other error (not 500)
            health["consecutive_5xx"] = 0
            log.info(f"HTTP {http_status} — {result.get('message', result.get('status'))}")

        save_health(health)
        update_ledger(result, solve_time, cost_usd, retry_num=attempt)
        break

    # If we get here, all attempts failed
    if args.json:
        print(json.dumps({
            "ts": utc_now(),
            "faucet": "lightningnetworkstores.com",
            "captcha_solve_time_s": round(solve_time, 1),
            "cost_usd": cost_usd,
            "attempts": args.max_retries + 1,
            "claim_result": last_result,
            "circuit_breaker_open": health.get("circuit_breaker_open", False),
        }, indent=2))

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
