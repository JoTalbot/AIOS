"""Tests for minimal/full/locked AIOS dependency roles."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.version import Version

from scripts.check_dependency_contract import dependency_contract

ROOT = Path(__file__).resolve().parents[1]


def test_dependency_contract_is_consistent() -> None:
    report = dependency_contract(ROOT)

    assert report["errors"] == []
    assert report["counts"] == {"minimal": 12, "direct": 47, "locked": 198}
    assert report["transitive_locked_count"] == 151


def test_websockets_constraint_matches_web3_compatible_lock() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    websocket_requirement = next(
        Requirement(raw) for raw in pyproject["project"]["dependencies"] if Requirement(raw).name == "websockets"
    )

    assert websocket_requirement.specifier.contains(Version("15.0.1"))
    assert not websocket_requirement.specifier.contains(Version("16.1.1"))


def test_dependency_contract_cli_strict_mode() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_dependency_contract.py", "--strict"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Contract errors: **0**" in result.stdout
