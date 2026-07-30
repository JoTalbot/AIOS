#!/usr/bin/env python3
"""Contract tests for railway-health-reader skill."""
import json, subprocess, sys
from pathlib import Path
SKILL_DIR = Path(__file__).resolve().parents[1]

def test_skill_contract_files_exist():
    assert (SKILL_DIR / "SKILL.md").exists()
    assert (SKILL_DIR / "code" / "run.py").exists()

def test_run_py_not_generic_runtime():
    code = (SKILL_DIR / "code" / "run.py").read_text()
    assert "generic_skill_runtime" not in code
    assert "check_railway_http" in code or "RAILWAY_URL" in code

def test_run_produces_valid_json():
    result = subprocess.run(
        [sys.executable, str(SKILL_DIR / "code" / "run.py"), "--json"],
        capture_output=True, text=True, timeout=30
    )
    data = json.loads(result.stdout)
    assert data.get("skill") == "railway-health-reader"
    assert "http" in data
    assert data.get("read_only") is True
