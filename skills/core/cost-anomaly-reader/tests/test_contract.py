#!/usr/bin/env python3
"""Contract tests for cost-anomaly-reader skill."""
import json, subprocess, sys
from pathlib import Path
SKILL_DIR = Path(__file__).resolve().parents[1]

def test_skill_contract_files_exist():
    assert (SKILL_DIR / "SKILL.md").exists()
    assert (SKILL_DIR / "code" / "run.py").exists()

def test_run_py_not_generic_runtime():
    code = (SKILL_DIR / "code" / "run.py").read_text()
    assert "generic_skill_runtime" not in code
    assert "check_aws_cost" in code or "check_docker_usage" in code

def test_run_produces_valid_json():
    result = subprocess.run(
        [sys.executable, str(SKILL_DIR / "code" / "run.py"), "--json"],
        capture_output=True, text=True, timeout=30
    )
    data = json.loads(result.stdout)
    assert data.get("skill") == "cost-anomaly-reader"
    assert data.get("read_only") is True
