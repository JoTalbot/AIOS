"""Tests for source/config tracking and runtime-data ignore boundaries."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.check_tracking_policy import tracking_contract

ROOT = Path(__file__).resolve().parents[1]


def test_tracking_contract_is_clean() -> None:
    report = tracking_contract(ROOT)

    assert report["errors"] == []
    assert report["tracked_stitch_build_files"] >= 41
    assert report["required_json_manifests"] == 6
    assert report["runtime_ignore_samples"] == 11


def test_tracking_contract_cli_strict_mode() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_tracking_policy.py", "--strict"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Contract errors: **0**" in result.stdout
