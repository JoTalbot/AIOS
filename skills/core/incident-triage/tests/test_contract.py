#!/usr/bin/env python3
"""Contract tests for incident-triage skill."""
import json, subprocess, sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]

def test_skill_contract_files_exist():
    assert (SKILL_DIR / "SKILL.md").exists()
    assert (SKILL_DIR / "code" / "run.py").exists()

def test_skill_has_real_algorithm():
    text = (SKILL_DIR / "SKILL.md").read_text()
    assert "P1" in text or "severity" in text.lower()

def test_run_py_not_generic_runtime():
    code = (SKILL_DIR / "code" / "run.py").read_text()
    assert "generic_skill_runtime" not in code, "Should not use generic runtime"
    assert "check_systemd" in code or "check_docker" in code or "check_disk" in code

def test_run_produces_valid_json():
    result = subprocess.run(
        [sys.executable, str(SKILL_DIR / "code" / "run.py"), "--json"],
        capture_output=True, text=True, timeout=15
    )
    data = json.loads(result.stdout)
    assert data.get("skill") == "incident-triage"
    assert "total_incidents" in data
    assert "by_severity" in data
    assert data.get("read_only") is True

def test_incident_severity_classification():
    result = subprocess.run(
        [sys.executable, str(SKILL_DIR / "code" / "run.py"), "--json"],
        capture_output=True, text=True, timeout=15
    )
    data = json.loads(result.stdout)
    for inc in data.get("incidents", []):
        assert inc.get("severity") in ("P1", "P2", "P3", "P4")
        assert "source" in inc
        assert "category" in inc
