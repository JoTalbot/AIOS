#!/usr/bin/env python3
"""Contract tests for nginx-route-auditor skill."""
import json, subprocess, sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]

def test_skill_contract_files_exist():
    assert (SKILL_DIR / "SKILL.md").exists()
    assert (SKILL_DIR / "code" / "run.py").exists()

def test_skill_has_real_algorithm():
    text = (SKILL_DIR / "SKILL.md").read_text()
    assert "nginx" in text.lower() and ("proxy" in text.lower() or "location" in text.lower())

def test_run_py_not_generic_runtime():
    code = (SKILL_DIR / "code" / "run.py").read_text()
    assert "generic_skill_runtime" not in code
    assert "parse_server_blocks" in code or "find_nginx_configs" in code

def test_run_produces_valid_json():
    result = subprocess.run(
        [sys.executable, str(SKILL_DIR / "code" / "run.py"), "--json"],
        capture_output=True, text=True, timeout=15
    )
    data = json.loads(result.stdout)
    assert data.get("skill") == "nginx-route-auditor"
    assert "configs_found" in data
    assert data.get("read_only") is True
