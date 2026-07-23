"""Verify all critical documentation files are present and non-empty."""
from pathlib import Path

ROOT = Path(__file__).parent.parent

DOCS = [
    "README.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md",
    "ARCHITECTURE.md", "EXECUTIVE_SUMMARY.md", "VERSION", "ROADMAP_NEXT.md",
    "Makefile", "pyproject.toml", "requirements.txt",
    ".editorconfig", ".gitignore", ".dockerignore",
    ".pre-commit-config.yaml", ".pylintrc", ".flake8", ".isort.cfg",
    ".bandit", ".git-blame-ignore-revs",
]

def test_all_docs_present():
    missing = [d for d in DOCS if not (ROOT / d).exists()]
    assert missing == [], f"Missing docs: {missing}"

def test_all_docs_nonempty():
    empty = [d for d in DOCS if (ROOT / d).exists() and (ROOT / d).stat().st_size == 0]
    assert empty == [], f"Empty docs: {empty}"

def test_vcs_files_present():
    for f in [".gitignore"]:
        assert (ROOT / f).exists(), f"Missing: {f}"

def test_tools_directory_nonempty():
    tools = list((ROOT / "tools").glob("*"))
    assert len(tools) > 0, "tools/ directory is empty"

def test_platforms_yaml_count():
    yamls = list((ROOT / "platforms").glob("*.yaml"))
    assert len(yamls) >= 3, f"Only {len(yamls)} platform YAML files"

def test_tests_directory_structure():
    for sub in ["chaos", "e2e", "integration", "load", "performance", "security"]:
        d = ROOT / "tests" / sub
        if d.exists():
            assert (d / "__init__.py").exists(), f"Missing __init__.py in tests/{sub}"

def test_github_templates():
    for f in ["PULL_REQUEST_TEMPLATE.md"]:
        p = ROOT / ".github" / f
        assert p.exists(), f"Missing: {f}"

def test_quality_tool_exists():
    assert (ROOT / "tools" / "quality_check.py").exists(), "Missing quality checker"
