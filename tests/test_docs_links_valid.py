"""Verify documentation links are valid."""
from pathlib import Path

ROOT = Path(__file__).parent.parent

def test_readme_references():
    content = (ROOT / "README.md").read_text()
    refs = ["ARCHITECTURE.md", "SECURITY.md", "CONTRIBUTING.md", "CHANGELOG.md"]
    for ref in refs:
        assert ref in content, f"Missing reference to {ref} in README"

def test_architecture_exists():
    arch = ROOT / "ARCHITECTURE.md"
    assert arch.exists() and arch.stat().st_size > 0

def test_constitution_dir():
    d = ROOT / "docs" / "constitution"
    if d.exists():
        assert len(list(d.glob("*.md"))) > 0
