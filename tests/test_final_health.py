"""Final comprehensive health check."""
from pathlib import Path
import ast, os

ROOT = Path(__file__).parent.parent

def test_no_bare_excepts():
    count = 0
    for f in (ROOT / "aios_core").rglob("*.py"):
        if f.name.startswith("__"): continue
        for line in open(f):
            if line.strip() == "except:" and "noqa" not in line:
                count += 1
    assert count == 0, f"Found {count} bare excepts"

def test_all_compile():
    errors = []
    for f in (ROOT / "aios_core").rglob("*.py"):
        try: ast.parse(f.read_text())
        except SyntaxError as e: errors.append(str(f.relative_to(ROOT)))
    assert errors == [], f"Compile errors: {errors}"

def test_init_files_present():
    missing = []
    for d in (ROOT / "aios_core").rglob("*/"):
        if "__pycache__" in str(d): continue
        if not (d / "__init__.py").exists():
            missing.append(str(d.relative_to(ROOT)))
    assert len(missing) <= 5, f"Missing __init__.py: {missing}"

def test_all_modules_have_all():
    missing_all = []
    for f in (ROOT / "aios_core").rglob("*.py"):
        if f.name.startswith("__"): continue
        content = f.read_text()
        if "class " in content and "__all__" not in content:
            missing_all.append(str(f.relative_to(ROOT)))
    assert len(missing_all) <= 10, f"Missing __all__: {missing_all[:5]}..."

def test_test_files_syntax():
    bad = []
    for f in (ROOT / "tests").glob("test_*.py"):
        try: ast.parse(f.read_text())
        except SyntaxError as e: bad.append(str(f.name))
    assert bad == [], f"Bad test files: {bad}"
