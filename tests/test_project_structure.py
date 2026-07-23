"""Verify project directory structure."""
from pathlib import Path

ROOT = Path(__file__).parent.parent

REQUIRED_DIRS = [
    "aios_core", "aios_core/api", "aios_core/modules", "aios_core/platforms",
    "tests", "docs", "platforms", "tools", "scripts", "deploy", "sdk",
    ".github", ".github/workflows",
]

def test_all_dirs_exist():
    missing = [d for d in REQUIRED_DIRS if not (ROOT / d).exists()]
    assert missing == [], f"Missing directories: {missing}"

def test_ci_workflow_count():
    wf = list((ROOT / ".github" / "workflows").glob("*.yml"))
    assert len(wf) >= 5, f"Only {len(wf)} CI workflows"

def test_python_package_structure():
    for sub in ["api", "modules", "platforms", "mcp", "test_engine"]:
        d = ROOT / "aios_core" / sub
        if d.exists():
            assert (d / "__init__.py").exists(), f"Missing __init__.py in aios_core/{sub}"
