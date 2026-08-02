"""Tests for Autocoder Memory"""
import tempfile
import pathlib
from aios_core.autocoder_memory import AutocoderMemory

def test_record_success(tmp_path):
    mem = AutocoderMemory(repo_path=str(tmp_path))
    mem.record_success("aios_core/test.py", "fix bug", "add check", 100, "groq", "security")
    assert len(mem.data["successful_fixes"]) == 1
    assert mem.data["file_stats"]["aios_core/test.py"]["fixes"] == 1
    assert mem.data["provider_stats"]["groq"]["success"] == 1

def test_record_failure(tmp_path):
    mem = AutocoderMemory(repo_path=str(tmp_path))
    mem.record_failure("aios_core/bad.py", "fix", "SyntaxError", "groq")
    assert len(mem.data["failed_attempts"]) == 1
    assert mem.data["file_stats"]["aios_core/bad.py"]["fails"] == 1

def test_best_provider(tmp_path):
    mem = AutocoderMemory(repo_path=str(tmp_path))
    mem.record_success("a.py", "fix", "do", 10, "groq", "")
    mem.record_success("b.py", "fix", "do", 10, "groq", "")
    mem.record_success("c.py", "fix", "do", 10, "groq", "")
    mem.record_failure("d.py", "fix", "err", "openrouter")
    assert mem.get_best_provider() == "groq"

def test_avoid_files(tmp_path):
    mem = AutocoderMemory(repo_path=str(tmp_path))
    for _ in range(4):
        mem.record_failure("aios_core/bad.py", "fix", "err", "groq")
    mem.record_success("aios_core/good.py", "fix", "do", 10, "groq", "")
    avoid = mem.get_avoid_files()
    assert "aios_core/bad.py" in avoid

def test_context_prompt(tmp_path):
    mem = AutocoderMemory(repo_path=str(tmp_path))
    mem.record_success("a.py", "security fix", "do", 10, "groq", "security-audit")
    ctx = mem.get_context_prompt("fix security vulnerability")
    assert "groq" in ctx or "security" in ctx.lower()
