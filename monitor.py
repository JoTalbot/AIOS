"""
AIOS Monitoring & Health Check Script
=====================================

Usage:
    python monitor.py [--url URL] [--interval SECONDS]

Checks health, metrics and basic system state.
"""

import argparse
import time
from datetime import datetime

import httpx


def check_health(base_url: str) -> dict:
    try:
        resp = httpx.get(f"{base_url}/health", timeout=5.0)
        return {"status": resp.status_code, "data": resp.json()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_metrics(base_url: str) -> dict:
    try:
        resp = httpx.get(f"{base_url}/metrics", timeout=5.0)
        return {"status": resp.status_code, "metrics": resp.text[:500]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_stats(base_url: str) -> dict:
    try:
        resp = httpx.get(f"{base_url}/api/v1/stats", timeout=5.0)
        return {"status": resp.status_code, "data": resp.json()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="AIOS Monitoring Tool")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL of AIOS REST API")
    parser.add_argument("--interval", type=int, default=30, help="Check interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    print(f"🔍 AIOS Monitor started — {datetime.now().isoformat()}")
    print(f"   Target: {args.url}")
    print()

    while True:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking...")

        health = check_health(args.url)
        metrics = check_metrics(args.url)
        stats = check_stats(args.url)

        print(f"  Health: {health.get('status')}")
        if "data" in health:
            print(f"    → {health['data']}")

        if metrics.get("status") == 200:
            print("  Metrics: OK (Prometheus format)")
        else:
            print(f"  Metrics: {metrics.get('status')}")

        if "data" in stats:
            s = stats["data"]
            print(
                f"  Stats: tasks={s.get('total_tasks', 0)} | memory={s.get('memory_items', 0)} | evolution={s.get('evolution_proposals', 0)}"
            )

        print()

        if args.once:
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
