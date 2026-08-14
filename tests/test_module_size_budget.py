"""Regression guard for incremental monolith decomposition."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.check_module_size_budget import module_size_report

ROOT = Path(__file__).resolve().parents[1]


def test_module_size_budget_is_not_exceeded() -> None:
    report = module_size_report(ROOT)

    assert report["errors"] == []
    assert report["modules"]["aios_core/quant_trading_engine.py"]["lines"] <= 1_900
    assert report["modules"]["aios_core/quant_report_formatters.py"]["lines"] <= 320


def test_module_size_budget_cli_strict_mode() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_module_size_budget.py", "--strict"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Contract errors: **0**" in result.stdout
