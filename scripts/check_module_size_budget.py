#!/usr/bin/env python3
"""Prevent known AIOS monoliths from growing while seams are extracted."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

MODULE_LINE_BUDGETS = {
    "aios_core/dashboard.py": 3_494,
    "tg_bot/accounts.py": 3_225,
    "run_account_control.py": 2_374,
    "aios_core/quant_trading_engine.py": 1_900,
    "aios_core/quant_report_formatters.py": 320,
}
TOP_LEVEL_SPAN_BUDGETS = {
    ("aios_core/dashboard.py", "AIOSDashboard"): 3_351,
    ("tg_bot/accounts.py", "_handle_account_intent"): 2_875,
    ("run_account_control.py", "main"): 401,
    ("aios_core/quant_trading_engine.py", "MultiExchangeQuantEngine"): 403,
    ("aios_core/quant_trading_engine.py", "format_multi_exchange_demo_report"): 131,
}


def module_size_report(root: Path) -> dict[str, Any]:
    """Return line/function span budget usage and violations."""

    root = root.resolve()
    errors: list[str] = []
    modules: dict[str, dict[str, int]] = {}
    trees: dict[str, ast.Module] = {}
    for relative, budget in MODULE_LINE_BUDGETS.items():
        path = root / relative
        text = path.read_text(encoding="utf-8")
        lines = len(text.splitlines())
        modules[relative] = {"lines": lines, "budget": budget}
        if lines > budget:
            errors.append(f"{relative}: {lines} lines exceeds budget {budget}; extract a seam instead of growing it")
        trees[relative] = ast.parse(text, filename=relative)

    spans: dict[str, dict[str, int]] = {}
    for (relative, symbol), budget in TOP_LEVEL_SPAN_BUDGETS.items():
        node = next(
            (
                item
                for item in trees[relative].body
                if isinstance(item, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == symbol
            ),
            None,
        )
        if node is None:
            errors.append(f"{relative}: top-level symbol {symbol} not found")
            continue
        span = (node.end_lineno or node.lineno) - node.lineno + 1
        key = f"{relative}:{symbol}"
        spans[key] = {"span": span, "budget": budget}
        if span > budget:
            errors.append(f"{key}: span {span} exceeds budget {budget}; route new logic to a submodule")

    return {"modules": modules, "spans": spans, "errors": errors}


def _render(report: dict[str, Any]) -> str:
    lines = ["# AIOS module size budget", ""]
    lines.extend(
        f"- `{path}`: {values['lines']} / {values['budget']} lines" for path, values in report["modules"].items()
    )
    lines.append(f"- Contract errors: **{len(report['errors'])}**")
    lines.extend(f"- ERROR: {error}" for error in report["errors"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    report = module_size_report(args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else _render(report), end="")
    return 1 if args.strict and report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
