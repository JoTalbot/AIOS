#!/usr/bin/env python3
"""Contract tests for config-drift-audit skill."""
import json, subprocess, sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]

def test_skill_contract_files_exist():
    assert (SKILL_DIR / "SKILL.md").exists()
    assert (SKILL_DIR / "code" / "run.py").exists()

def test_skill_has_real_algorithm():
    text = (SKILL_DIR / "SKILL.md").read_text()
    assert "drift" in text.lower() or "canonical" in text.lower()

def test_run_py_not_generic_runtime():
    code = (SKILL_DIR / "code" / "run.py").read_text()
    assert "generic_skill_runtime" not in code
    assert "file_hash" in code or "check_env_secrets" in code

def test_run_produces_valid_json():
    result = subprocess.run(
        [sys.executable, str(SKILL_DIR / "code" / "run.py"), "--json"],
        capture_output=True, text=True, timeout=15
    )
    data = json.loads(result.stdout)
    assert data.get("skill") == "config-drift-audit"
    assert "total_drifts" in data
    assert "canonical_paths_checked" in data
    assert data.get("read_only") is True
