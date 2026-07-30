#!/usr/bin/env python3
"""master_faucet_loop.py v2 — Master loop runner for all working faucets.

Runs cyclically:
  1. Stakely POL (Playwright, ~15 min cooldown, FREE — Turnstile auto-solves)
  2. LNS BTC (API + hCaptcha 2Captcha, ~$0.002/solve, with auto-retry + circuit breaker)

Changes v2:
  - LNS uses lns_with_retry.py (3 retries, exponential backoff, circuit breaker)
  - Better budget tracking
  - Health status reporting
  - Configurable per-faucet intervals

Usage:
  python3 master_faucet_loop.py                   # infinite loop
  python3 master_faucet_loop.py --iterations 5    # 5 iterations
  python3 master_faucet_loop.py --interval 300    # 5 min between iterations
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(os.environ.get("OCTOPUS_ME_SKILL_DIR") or Path(__file__).resolve().parents[1])
CONFIG = SKILL_DIR / "config"
DATA = SKILL_DIR / "data"
FAUCET_CFG = CONFIG / "faucet_config.json"
LEDGER = DATA / "faucet_ledger.json"
BUDGET_FILE = DATA / "daily_captcha_budget.json"
LNS_HEALTH = DATA / "lns_health.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(DATA / "master_loop.log"), mode="a"),
    ],
)
log = logging.getLogger("master")


def load_json(p, d=None):
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if d is not None and isinstance(d, dict):
            if not isinstance(data, dict):
                return d.copy() if isinstance(d, dict) else d
        return data
    except Exception:
        return d.copy() if isinstance(d, dict) else d if d is not None else {}


def save_json(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def check_budget(config):
    budget_cfg = config.get("captcha", {})
    max_daily = budget_cfg.get("max_daily_budget_usd", 0.5)
    cost_per = budget_cfg.get("max_cost_per_solve_usd", 0.003)

    budget_data = load_json(BUDGET_FILE, {"date": "", "spent_usd": 0.0, "solves": 0})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if budget_data.get("date") != today:
        budget_data = {"date": today, "spent_usd": 0.0, "solves": 0}
        save_json(BUDGET_FILE, budget_data)

    remaining = max_daily - budget_data["spent_usd"]
    if remaining < cost_per:
        log.warning(f"Budget exhausted: spent ${budget_data['spent_usd']:.4f} / ${max_daily}")
        return False, budget_data
    return True, budget_data


def run_stakely_pol():
    """Run Stakely POL faucet (free, Turnstile auto-solves)."""
    log.info("[STAKELY-POL] Starting...")
    try:
        result = subprocess.run(
            [str(SKILL_DIR / 'code' / 'with_external_effect_lock.sh'), sys.executable, str(SKILL_DIR / 'code' / 'stakely_claimer.py'), '--coin', 'polygon-pol'],
            capture_output=True, text=True, timeout=120, cwd=str(SKILL_DIR),
            env={**os.environ, "OCTOPUS_ME_SKILL_DIR": str(SKILL_DIR)},
        )
        output = result.stdout + result.stderr
        for line in output.strip().split("\n"):
            if line.strip():
                log.info(f"[STAKELY-POL] {line.strip()}")

        if "claimed" in output.lower():
            return {"status": "claimed", "details": "Stakely POL claimed"}
        return {"status": "failed", "details": output[-300:] if output else "no output"}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "details": "120s timeout"}
    except Exception as e:
        return {"status": "error", "details": str(e)[:200]}


def run_lns():
    """Run LNS BTC faucet with auto-retry and circuit breaker."""
    log.info("[LNS-BTC] Starting (with retry)...")

    # Check circuit breaker first (without spending captcha budget)
    health = load_json(LNS_HEALTH, {})
    if health.get("circuit_breaker_open"):
        opened_at = health.get("circuit_breaker_opened_at", "")
        consec = health.get("consecutive_5xx", 0)
        log.info(f"[LNS-BTC] Circuit breaker OPEN — {consec} consecutive 500s (since {opened_at[:19]})")
        return {
            "status": "circuit_breaker",
            "details": f"Skipping LNS — circuit breaker open after {consec} consecutive 500s",
        }

    try:
        result = subprocess.run(
            [str(SKILL_DIR / 'code' / 'with_external_effect_lock.sh'), sys.executable, str(SKILL_DIR / 'code' / 'lns_with_retry.py')],
            capture_output=True, text=True, timeout=300,  # 5 min max (captcha + retries)
            cwd=str(SKILL_DIR),
            env={**os.environ, "OCTOPUS_ME_SKILL_DIR": str(SKILL_DIR)},
        )
        output = result.stdout + result.stderr
        for line in output.strip().split("\n"):
            if line.strip():
                log.info(f"[LNS-BTC] {line.strip()}")

        exit_code = result.returncode

        if exit_code == 0:
            return {"status": "claimed", "details": "LNS BTC claimed"}
        elif exit_code == 2:
            return {"status": "circuit_breaker", "details": "Circuit breaker opened"}
        elif "500" in output:
            return {"status": "backend_error", "details": "LNS backend 500 (all retries failed)"}
        elif "Budget" in output or "budget" in output:
            return {"status": "no_budget", "details": "Budget exhausted"}
        else:
            return {"status": "failed", "details": output[-300:] if output else "no output"}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "details": "300s timeout"}
    except Exception as e:
        return {"status": "error", "details": str(e)[:200]}




def run_lightningfaucet():
    """Run LightningFaucet - Free Spin + wallet balance check."""
    log.info("[LIGHTNINGFAUCET] Starting...")
    # Check wallet balance (free, no browser)
    try:
        cfg = load_json(FAUCET_CFG, {})
        api_key = cfg.get("lightningfaucet", {}).get("api_key", "")
        if api_key:
            import subprocess as _sp
            env = {**os.environ, "LIGHTNING_WALLET_API_KEY": api_key}
            r = _sp.run(["lw", "balance"], capture_output=True, text=True, timeout=15, env=env)
            if r.stdout.strip():
                try:
                    bal = json.loads(r.stdout.strip())
                    log.info(f"[LIGHTNINGFAUCET] Wallet: {bal.get('balance_sats', 0)} sats")
                except:
                    pass
    except Exception as e:
        log.debug(f"[LF] Balance check: {e}")

    # Try free spin via Playwright
    try:
        result = subprocess.run(
            [str(SKILL_DIR / 'code' / 'with_external_effect_lock.sh'), sys.executable, str(SKILL_DIR / 'code' / 'lightningfaucet_claimer.py'), '--spin'],
            capture_output=True, text=True, timeout=120, cwd=str(SKILL_DIR),
            env={**os.environ, "OCTOPUS_ME_SKILL_DIR": str(SKILL_DIR)},
        )
        output = result.stdout + result.stderr
        for line in output.strip().split("\n"):
            if line.strip():
                log.info(f"[LIGHTNINGFAUCET] {line.strip()}")

        if "claimed" in output.lower():
            return {"status": "claimed", "details": "LF spin claimed"}
        elif "need_login" in output.lower():
            return {"status": "need_login", "details": "LF needs login"}
        elif "cooldown" in output.lower():
            return {"status": "cooldown", "details": "LF on cooldown"}
        return {"status": "failed", "details": output[-200:] if output else "no output"}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "details": "120s timeout"}
    except Exception as e:
        return {"status": "error", "details": str(e)[:200]}

def print_health_summary():
    """Print current health status."""
    health = load_json(LNS_HEALTH, {})
    budget = load_json(BUDGET_FILE, {"date": "", "spent_usd": 0.0, "solves": 0})

    log.info("─── Health Summary ───")
    log.info(f"  LNS total attempts:  {health.get('total_attempts', 0)}")
    log.info(f"  LNS successes:       {health.get('total_successes', 0)}")
    log.info(f"  LNS 500 errors:      {health.get('total_5xx_errors', 0)}")
    log.info(f"  LNS consec 500s:     {health.get('consecutive_5xx', 0)}")
    log.info(f"  LNS circuit breaker: {'OPEN' if health.get('circuit_breaker_open') else 'CLOSED'}")
    last_success = health.get('last_success') or 'never'
    last_5xx = health.get('last_5xx') or 'never'
    log.info(f"  LNS last success:    {str(last_success)[:19]}")
    log.info(f"  LNS last 500:        {str(last_5xx)[:19]}")
    log.info(f"  LNS captcha solved:  {health.get('total_captcha_solved', 0)}")
    log.info(f"  LNS captcha cost:    ${health.get('total_captcha_cost_usd', 0):.4f}")
    log.info(f"  Daily budget used:   ${budget.get('spent_usd', 0):.4f}")
    log.info("──────────────────────")


def main():
    parser = argparse.ArgumentParser(description="Master Faucet Loop Runner v2")
    parser.add_argument("--iterations", type=int, default=0, help="Max iterations (0=unlimited)")
    parser.add_argument("--interval", type=int, default=300, help="Interval between iterations (s)")
    parser.add_argument("--skip-stakely", action="store_true")
    parser.add_argument("--skip-lns", action="store_true")
    parser.add_argument("--skip-lightningfaucet", action="store_true")
    parser.add_argument("--health", action="store_true", help="Show health and exit")
    args = parser.parse_args()

    config = load_json(FAUCET_CFG, {})

    if args.health:
        print_health_summary()
        return

    iteration = 0
    total_claimed = 0
    total_stakely = 0
    total_lns = 0
    total_lf = 0

    log.info(f"Master loop v2 started. Interval={args.interval}s")
    log.info(f"Budget: ${config.get('captcha',{}).get('max_daily_budget_usd', 0.5)}/day")

    while True:
        iteration += 1
        if args.iterations and iteration > args.iterations:
            log.info(f"Max iterations ({args.iterations}) reached. Stopping.")
            break

        log.info(f"{'='*60} ITERATION #{iteration} {'='*60}")

        can_spend, budget_data = check_budget(config)

        # ── Stakely POL (free) ──
        if not args.skip_stakely:
            r = run_stakely_pol()
            if r["status"] == "claimed":
                total_claimed += 1
                total_stakely += 1
                log.info(f"[RESULT] Stakely POL: CLAIMED!")
            else:
                log.info(f"[RESULT] Stakely POL: {r['status']} — {r['details'][:100]}")

        # ── LNS BTC (costs ~$0.002) ──
        if not args.skip_lns:
            if r := run_lns():
                if r["status"] == "claimed":
                    total_claimed += 1
                    total_lns += 1
                    log.info(f"[RESULT] LNS BTC: CLAIMED!")
                elif r["status"] == "circuit_breaker":
                    log.info(f"[RESULT] LNS BTC: {r['details'][:100]}")
                elif r["status"] == "no_budget":
                    log.info(f"[RESULT] LNS BTC: Budget exhausted")
                else:
                    log.info(f"[RESULT] LNS BTC: {r['status']} — {r['details'][:100]}")

        # ── LightningFaucet (Free Spin + wallet) ──
        if not args.skip_lightningfaucet:
            r = run_lightningfaucet()
            if r["status"] == "claimed":
                total_claimed += 1
                total_lf += 1
                log.info("[RESULT] LightningFaucet: CLAIMED!")
            elif r["status"] == "need_login":
                log.info("[RESULT] LightningFaucet: needs login (skipping)")
            elif r["status"] == "cooldown":
                log.info("[RESULT] LightningFaucet: on cooldown")
            else:
                log.info(f"[RESULT] LightningFaucet: {r['status']} - {r['details'][:100]}")

        # ── Summary ──
        log.info(f"[SUMMARY] #{iteration} | Claimed: {total_claimed} "
                 f"(Stakely: {total_stakely}, LNS: {total_lns}, LF: {total_lf}) | "
                 f"Budget: ${budget_data.get('spent_usd', 0):.4f}")

        # Print health every 5 iterations
        if iteration % 5 == 0:
            print_health_summary()

        if args.interval > 0:
            log.info(f"Sleeping {args.interval}s...")
            time.sleep(args.interval)


if __name__ == "__main__":
    main()