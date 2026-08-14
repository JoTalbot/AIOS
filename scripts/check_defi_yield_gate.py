#!/usr/bin/env python3
"""Risk-adjusted read-only gate for DeFi yield recommendations."""

import argparse
import json
from pathlib import Path

HAIRCUT = {"lending": 2.0, "native_staking": 20.0, "liquidity_pool": 8.0}


def evaluate(state):
    alloc = state.get("current_allocation") or {}
    opportunities = []
    for item in state.get("all_opportunities") or []:
        risk = HAIRCUT.get(item.get("type"), 10.0)
        adjusted = float(item.get("apy_pct", 0)) - risk
        mock = bool((alloc.get(item.get("network")) or {}).get("is_mock", True))
        opportunities.append(
            {**item, "risk_haircut_pct": risk, "risk_adjusted_apy_pct": round(adjusted, 4), "is_mock": mock}
        )
    best = max(opportunities, key=lambda x: x["risk_adjusted_apy_pct"], default=None)
    bridge = state.get("bridge_quote") or {}
    current = state.get("current_network")
    current_balance = float((alloc.get(current) or {}).get("balance_usd", 0) or 0)
    checks = {
        "current_balance_positive": current_balance > 0,
        "destination_live": bool(best and not best["is_mock"]),
        "adjusted_apy_positive": bool(best and best["risk_adjusted_apy_pct"] > 0),
        "bridge_not_stub": bool(bridge and "stub" not in str(bridge.get("provider", "")).lower()),
    }
    return {
        "ready": all(checks.values()),
        "checks": checks,
        "best": best,
        "opportunities": opportunities,
        "execution": "read_only",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--state", type=Path, default=Path("data/liquidity_router_state.json"))
    p.add_argument("--output", type=Path, default=Path("data/reports/defi_yield_gate.json"))
    a = p.parse_args()
    r = evaluate(json.loads(a.state.read_text()))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n")
    print(f"ready={r['ready']} failed={[k for k, v in r['checks'].items() if not v]}")
    return 0 if r["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
