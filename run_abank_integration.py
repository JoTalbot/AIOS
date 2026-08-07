#!/usr/bin/env python3
"""Safe A-Банк integration CLI.

Commands never log in to a bank, open a banking app, send a payment or call a
remote banking endpoint.  Business signatures are built locally only.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from aios_core.banking import BankingService

ROOT = Path(__file__).resolve().parent


def _service(args: argparse.Namespace) -> BankingService:
    return BankingService(root=args.data_root or os.getenv("AIOS_BANKING_DATA", ROOT / "data" / "banking"))


def main() -> int:
    parser = argparse.ArgumentParser(description="AIOS safe A-Банк integration")
    parser.add_argument("command", choices=("status", "import-csv", "import-json", "import-pdf", "transactions", "business-status", "business-sign"))
    parser.add_argument("--subject", default="cli", help="Local owner subject; never used as a bank login")
    parser.add_argument("--data-root", default="", help="Local root for permissioned local storage")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--account-id", default="manual")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--since", default=None)
    parser.add_argument("--endpoint", default="getLoanStatus")
    parser.add_argument("--body-json", default="{}")
    parser.add_argument("--secret-env", default="AIOS_ABANK_BUSINESS_SECRET")
    args = parser.parse_args()

    service = _service(args)
    if args.command == "status":
        result = service.status(args.subject)
    elif args.command == "business-status":
        result = service.business_api.safety_status()
    elif args.command == "transactions":
        result = {"status": "ok", "transactions": service.list_transactions(args.subject, limit=args.limit, since=args.since)}
    elif args.command in {"import-csv", "import-json", "import-pdf"}:
        if not args.file or not args.file.is_file():
            parser.error("--file must point to a local statement file")
        if args.command == "import-pdf":
            result = service.import_pdf(args.subject, args.file, account_id=args.account_id).to_dict()
        else:
            content = args.file.read_bytes()
            result = service.import_content(args.subject, content, format=args.command.removeprefix("import-"), account_id=args.account_id).to_dict()
    else:
        secret = os.getenv(args.secret_env, "")
        if not secret:
            parser.error(f"secret must be provided through environment variable {args.secret_env}")
        try:
            payload = json.loads(args.body_json)
        except json.JSONDecodeError as exc:
            parser.error(f"--body-json must be valid JSON: {exc}")
        if not isinstance(payload, dict):
            parser.error("--body-json must be a JSON object")
        result = service.business_api.build_request(args.endpoint, payload, secret=secret).to_dict()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
