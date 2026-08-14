"""Regression tests for deterministic repository inventory."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.generate_project_inventory import project_inventory

ROOT = Path(__file__).resolve().parents[1]


def test_project_inventory_has_no_python_syntax_errors() -> None:
    data = project_inventory(ROOT)

    assert data["version"] == (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert data["python_syntax_errors"] == []
    assert data["python"]["files"] > 3_000
    assert data["test_functions"] > 5_000
    assert len(data["compose"]["docker-compose.prod.yml"]) >= 10


def test_generated_project_inventory_is_current() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/generate_project_inventory.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "current docs/PROJECT_INVENTORY.md" in result.stdout


def test_inventory_ignores_unstaged_worktree_changes() -> None:
    """Parallel agent diffs must not make the index-derived snapshot stale."""

    readme = ROOT / "README.md"
    original = readme.read_text(encoding="utf-8")
    before = project_inventory(ROOT)
    try:
        readme.write_text(original + "\nunstaged inventory probe\n", encoding="utf-8")
        after = project_inventory(ROOT)
    finally:
        readme.write_text(original, encoding="utf-8")
    assert after["lines"] == before["lines"]
    assert after["bytes"] == before["bytes"]
