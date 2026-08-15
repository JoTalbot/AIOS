#!/usr/bin/env python3
"""Q5: subscription management for the MM signal product.

Manages data/quant_subscriptions.json: active subscribers with tokens, tiers,
expiry. The signal emitter broadcasts to active subscribers.

Commands:
    python scripts/subscription_manage.py add --chat <id> [--days 30] [--tier basic]
    python scripts/subscription_manage.py list
    python scripts/subscription_manage.py revoke <token>
    python scripts/subscription_manage.py clean   (deactivate expired)
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

FILE = Path("/root/AIOS/data/quant_subscriptions.json")


def load() -> dict:
    if FILE.exists():
        d = json.loads(FILE.read_text())
        if isinstance(d, dict):
            return d
    return {"subscribers": []}


def save(d: dict) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2))


def active_subscribers(d: dict) -> list[dict]:
    today = datetime.now(UTC).date().isoformat()
    out = []
    for s in d.get("subscribers", []):
        if s.get("active") and (not s.get("expires") or s["expires"] >= today):
            out.append(s)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add")
    p.add_argument("--chat", type=int, required=True)
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--tier", default="basic")

    p = sub.add_parser("list")
    p = sub.add_parser("clean")

    p = sub.add_parser("revoke")
    p.add_argument("token")

    args = ap.parse_args()
    d = load()

    if args.cmd == "add":
        token = secrets.token_hex(8)
        expires = (datetime.now(UTC) + timedelta(days=args.days)).date().isoformat()
        d["subscribers"].append({
            "token": token, "chat_id": args.chat, "tier": args.tier,
            "active": True, "expires": expires,
            "created": datetime.now(UTC).date().isoformat(),
        })
        save(d)
        print(f"added: token={token} chat={args.chat} tier={args.tier} expires={expires}")
        return 0

    if args.cmd == "list":
        for s in d.get("subscribers", []):
            mark = "active" if s.get("active") else "revoked"
            print(f"{s['token']} chat={s['chat_id']} tier={s['tier']} "
                  f"expires={s.get('expires')} [{mark}]")
        print(f"active: {len(active_subscribers(d))}")
        return 0

    if args.cmd == "revoke":
        for s in d.get("subscribers", []):
            if s["token"] == args.token:
                s["active"] = False
                save(d)
                print(f"revoked {args.token}")
                return 0
        print("token not found")
        return 1

    if args.cmd == "clean":
        today = datetime.now(UTC).date().isoformat()
        n = 0
        for s in d.get("subscribers", []):
            if s.get("active") and s.get("expires") and s["expires"] < today:
                s["active"] = False
                n += 1
        save(d)
        print(f"deactivated {n} expired")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
