"""Release-version consistency checks without importing the side-effect-heavy root app."""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

import aios_core
from aios_core import p2p_network

ROOT = Path(__file__).resolve().parents[1]
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")


def _string_assignment(path: Path, name: str) -> str:
    """Return a module-level string assignment without importing the module."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return node.value.value
    raise AssertionError(f"String assignment {name!r} not found in {path}")


def test_release_version_is_consistent() -> None:
    """VERSION, package metadata and lightweight public API must agree."""

    version_file = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    pyproject_version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]

    assert SEMVER_RE.fullmatch(version_file), f"VERSION is not SemVer: {version_file!r}"
    assert version_file == pyproject_version == aios_core.__version__
    assert p2p_network.app.version == version_file


def test_root_fastapi_uses_canonical_package_version() -> None:
    """The root FastAPI app must not reintroduce a hard-coded release literal."""

    path = ROOT / "main.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    imports_canonical_alias = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "aios_core"
        and any(alias.name == "__version__" and alias.asname == "AIOS_VERSION" for alias in node.names)
        for node in tree.body
    )
    assert imports_canonical_alias, "main.py must import aios_core.__version__ as AIOS_VERSION"

    app_assignment = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "app" for target in node.targets)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "FastAPI"
        ),
        None,
    )
    assert app_assignment is not None, "root FastAPI app assignment not found"
    version_keyword = next((kw for kw in app_assignment.value.keywords if kw.arg == "version"), None)
    assert version_keyword is not None
    assert isinstance(version_keyword.value, ast.Name) and version_keyword.value.id == "AIOS_VERSION"


def test_docs_workflow_reads_version_file() -> None:
    """Documentation publication must follow VERSION instead of a stale literal."""

    workflow = (ROOT / ".github" / "workflows" / "docs.yml").read_text(encoding="utf-8")
    assert "- 'VERSION'" in workflow
    assert "DOCS_VERSION: ${{ steps.project-version.outputs.version }}" in workflow
    assert 'mike deploy --push --update-aliases "$DOCS_VERSION" latest' in workflow
    assert "mike deploy --push --update-aliases 9.3.0 latest" not in workflow


def test_sdk_version_is_internally_consistent() -> None:
    """The independently released SDK keeps its own metadata and module version aligned."""

    sdk_pyproject = tomllib.loads((ROOT / "sdk" / "pyproject.toml").read_text(encoding="utf-8"))
    sdk_version = sdk_pyproject["project"]["version"]
    sdk_init = ROOT / "sdk" / "__init__.py"

    assert _string_assignment(sdk_init, "__version__") == sdk_version
    assert f"AIOS Python SDK v{sdk_version}" in (ast.get_docstring(ast.parse(sdk_init.read_text())) or "")
