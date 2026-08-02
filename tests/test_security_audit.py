"""Tests for security_audit module"""
import tempfile
import pathlib
from aios_core.security_audit import SecurityAuditor

def test_audit_xss(tmp_path):
    # Create file with innerHTML - ensure path does not contain "test" substring for xss check
    # xss check skips if "test" in str(fpath), so we need to bypass by using tmp dir without test
    # Instead test via direct content check
    aud = SecurityAuditor(repo_path=str(tmp_path))
    # Create file that will be detected
    f = tmp_path / "bad.py"
    f.write_text("element.innerHTML = user_input")
    # Temporarily check logic: audit_xss filters by "test" in path, which would filter tmp_path if it contains test_
    # So we create a subdir without test
    sub = tmp_path / "src"
    sub.mkdir()
    f2 = sub / "evil.py"
    f2.write_text("el.innerHTML = user_input")
    aud2 = SecurityAuditor(repo_path=str(sub))
    issues = aud2.audit_xss()
    assert len(issues) >= 1
    assert issues[0]["type"] in ("xss", "potential_xss")

def test_audit_secrets(tmp_path):
    f = tmp_path / "secrets.py"
    f.write_text("key = 'sk-or-v1-abc123def456ghi789jkl'")
    aud = SecurityAuditor(repo_path=str(tmp_path))
    issues = aud.audit_secrets()
    assert isinstance(issues, list)

def test_audit_dangerous_calls(tmp_path):
    # dangerous_calls only checks aios_core/ prefix in original implementation
    # So we test by creating aios_core structure inside tmp
    core_dir = tmp_path / "aios_core"
    core_dir.mkdir()
    f = core_dir / "danger.py"
    f.write_text("eval(user_input)")
    aud = SecurityAuditor(repo_path=str(tmp_path))
    issues = aud.audit_dangerous_calls()
    assert len(issues) >= 1

def test_generate_report():
    aud = SecurityAuditor(repo_path=".")
    rep = aud.generate_report()
    assert "xss" in rep
    assert "secrets" in rep
    assert "dangerous_calls" in rep

def test_audit_clean_file(tmp_path):
    sub = tmp_path / "src"
    sub.mkdir()
    f = sub / "clean.py"
    f.write_text("def add(a,b): return a+b")
    aud = SecurityAuditor(repo_path=str(sub))
    assert aud.audit_xss() == []
