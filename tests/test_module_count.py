"""Verify project module and test file counts."""
from pathlib import Path

ROOT = Path(__file__).parent.parent

def test_core_module_count():
    py_files = list((ROOT / "aios_core").rglob("*.py"))
    assert len(py_files) >= 300, f"Only {len(py_files)} core files"

def test_test_file_count():
    test_files = list((ROOT / "tests").glob("test_*.py"))
    assert len(test_files) >= 100, f"Only {len(test_files)} test files"

def test_platform_count():
    yamls = list((ROOT / "platforms").glob("*.yaml"))
    assert len(yamls) >= 5, f"Only {len(yamls)} platforms"

def test_ci_workflow_count():
    wf = list((ROOT / ".github" / "workflows").glob("*.yml"))
    assert len(wf) >= 5, f"Only {len(wf)} CI workflows"

def test_doc_md_count():
    docs = list((ROOT / "docs").rglob("*.md"))
    assert len(docs) >= 50, f"Only {len(docs)} doc files"
