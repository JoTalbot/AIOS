#!/usr/bin/env python3
"""airdrop_checker.py — read-only проверка незаявленных airdrop по публичному адресу.

Поддерживаемые сети: EVM (0x...), Cosmos (cosmos1...), Solana.

Источники:
  - Bankless Claimables API (требует BANKLESS_API_KEY, read-only).
  - Ручные ссылки для пользователя (fallback если ключа нет).

Безопасность:
  - Только публичный адрес; приватные ключи/seed НЕ запрашиваются и НЕ используются.
  - Никаких транзакций, claim-ов, подписей.
  - Bounded: таймауты, без retry-loop.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import requests
except Exception:
    requests = None  # type: ignore


RE_EVM = re.compile(r"^0x[a-fA-F0-9]{40}$")
RE_COSMOS = re.compile(r"^(cosmos|osmo|noble|celestia)1[a-z0-9]{38,58}$")
RE_SOLANA = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def detect_chain(addr: str) -> str:
    if RE_EVM.match(addr):
        return "evm"
    if RE_COSMOS.match(addr):
        return "cosmos"
    if RE_SOLANA.match(addr) and not addr.lower().startswith("cosmos") and not addr.lower().startswith("osmo"):
        return "solana"
    return "unknown"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_bankless(address: str, api_key: Optional[str]) -> Dict[str, Any]:
    """Проверка через Bankless Claimables API. Требует BANKLESS_API_KEY."""
    result = {"source": "bankless_claimables", "ok": False, "unclaimed": [], "error": None}
    if not api_key:
        result["error"] = "BANKLESS_API_KEY не задан. Запросите токен по email api@bankless.com (см. docs.bankless.com/authentication) или проверьте вручную на bankless.com/claimables"
        return result
    if requests is None:
        result["error"] = "модуль requests не установлен"
        return result
    try:
        url = f"https://api.bankless.com/claimables/{address}"
        r = requests.get(url, headers={
            "X-BANKLESS-TOKEN": api_key,
            "User-Agent": "Octopus-airdrop-checker/1.0",
            "Accept": "application/json"
        }, timeout=20)
        if r.status_code == 200:
            data = r.json()
            if not isinstance(data, list):
                data = []
            unclaimed = [x for x in data if x.get("claimStatus") == "unclaimed"]
            result["ok"] = True
            result["total_found"] = len(data)
            result["unclaimed_count"] = len(unclaimed)
            result["unclaimed"] = [
                {
                    "title": x.get("title"),
                    "supplier": x.get("supplier", {}).get("name"),
                    "type": x.get("type"),
                    "token_amount": x.get("tokenAmount"),
                    "token_name": x.get("tokenName"),
                    "worth_usd": x.get("worth", {}).get("worthUSDFloat"),
                    "action_url": x.get("action", {}).get("url"),
                    "expires": x.get("expires")
                }
                for x in unclaimed
            ]
        elif r.status_code == 401:
            result["error"] = "401 Unauthorized: неверный или отсутствующий BANKLESS_API_KEY"
        else:
            result["error"] = f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        result["error"] = str(e)
    return result


def build_report(address: str, api_key: Optional[str]) -> Dict[str, Any]:
    chain = detect_chain(address)
    bankless = check_bankless(address, api_key)
    report = {
        "skill": "money-earner-orchestrator/airdrop_checker",
        "vector": "САМООБЕСПЕЧЕНИЕ",
        "tier": "L0",
        "ts": utc_now(),
        "address": address,
        "chain_detected": chain,
        "read_only": True,
        "private_key_used": False,
        "bankless": bankless,
        "manual_links": {
            "bankless_claimables": f"https://www.bankless.com/claimables?address={address}",
            "earni_fi": f"https://earni.fi/{address}",
            "drops_bot": f"https://www.drops.bot/airdrops/ethereum-airdrop-checker?address={address}",
            "airdropalert": "https://airdropalert.com/"
        },
        "notes": [
            "Bankless Claimables API требует BANKLESS_API_KEY (read-only). В документации заголовок: X-BANKLESS-TOKEN.",
            "Earni.fi имеет бесплатный preview, полный отчёт — paid.",
            "Для Cosmos-адресов используйте bankless.com/claimables с выбором сети."
        ]
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="airdrop_checker — read-only eligibility check")
    ap.add_argument("address", help="Публичный адрес кошелька (EVM/Cosmos/Solana)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--api-key", default=os.environ.get("BANKLESS_API_KEY"), help="Bankless API key (или env BANKLESS_API_KEY)")
    args = ap.parse_args()

    if detect_chain(args.address) == "unknown":
        print(f"[error] Неизвестный формат адреса: {args.address}", file=sys.stderr)
        return 1

    rep = build_report(args.address, args.api_key)
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print(f"[airdrop_checker] address={rep['address']} chain={rep['chain_detected']}")
        print(f"  Bankless: ok={rep['bankless']['ok']} unclaimed={rep['bankless'].get('unclaimed_count', 'N/A')}")
        if rep["bankless"].get("error"):
            print(f"  Bankless error: {rep['bankless']['error']}")
        print("  Manual links:")
        for name, url in rep["manual_links"].items():
            print(f"    - {name}: {url}")
        if rep["bankless"].get("unclaimed"):
            print("  Unclaimed found:")
            for u in rep["bankless"]["unclaimed"]:
                print(f"    - {u.get('title')} ({u.get('supplier')}): {u.get('token_amount')} {u.get('token_name')} ≈ ${u.get('worth_usd')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
