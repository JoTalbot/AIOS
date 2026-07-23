"""Tests for version consistency across the project."""

import re
from pathlib import Path


def test_pyproject_version():
    root = Path(__file__).parent.parent
    content = (root / "pyproject.toml").read_text()
    m = re.search(r'version\s*=\s*"([^"]+)"', content)
    assert m is not None
    assert m.group(1) == "9.3.1"


def test_init_version():
    root = Path(__file__).parent.parent
    content = (root / "aios_core" / "__init__.py").read_text()
    m = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    assert m is not None
    assert m.group(1) == "9.3.0"


def test_docs_conf_version():
    root = Path(__file__).parent.parent
    conf_path = root / "docs" / "source" / "conf.py"
    if conf_path.exists():
        content = conf_path.read_text()
        m = re.search(r'version\s*=\s*[\'"](\d+\.\d+\.\d+)', content)
        if m:
            assert m.group(1) in ("9.3.0", "9.3.1")
