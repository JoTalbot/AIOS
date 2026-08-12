from pathlib import Path
import tomllib

import aios_core
from aios_core import p2p_network


def test_release_version_is_consistent():
    root = Path(__file__).resolve().parents[1]
    version_file = (root / "VERSION").read_text().strip()
    pyproject_version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    assert version_file == pyproject_version == aios_core.__version__
    assert p2p_network.app.version == aios_core.__version__
