"""Tests for Autocoder v3"""
import pathlib
from aios_core.autocoder_v3 import AutocoderV3, AutoPRCreator

def test_v3_index(tmp_path):
    core = tmp_path / "aios_core"
    core.mkdir()
    (core / "test.py").write_text("def add(a,b): return a+b")
    v3 = AutocoderV3(repo_path=str(tmp_path))
    v3.ensure_indexed()
    assert len(v3.rag.indexed_files) >= 1

def test_v3_extract_code():
    v3 = AutocoderV3(repo_path=".")
    code = v3._extract_code("```python\ndef add(a,b): return a+b\n```")
    assert "def add" in code
    code2 = v3._extract_code("def foo(): pass")
    assert "def foo" in code2

def test_v3_apply_fix(tmp_path):
    v3 = AutocoderV3(repo_path=str(tmp_path))
    ok = v3.apply_fix("test.py", "def hello(): return 'hi'")
    assert ok
    assert (tmp_path / "test.py").exists()

def test_pr_creator_no_token(tmp_path):
    pr = AutoPRCreator(repo_path=str(tmp_path))
    pr.github_token = ""
    res = pr.create_branch_and_pr("test.py", "fix")
    assert not res["ok"]

def test_v3_memory_integration(tmp_path):
    v3 = AutocoderV3(repo_path=str(tmp_path))
    v3.memory.record_success("a.py", "fix", "do", 10, "groq", "")
    assert v3.memory.get_best_provider() == "groq"
