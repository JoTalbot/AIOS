"""Verify documentation structure."""

from pathlib import Path


def test_readme_exists():
    root = Path(__file__).parent.parent
    assert (root / "README.md").exists()


def test_changelog_exists():
    root = Path(__file__).parent.parent
    assert (root / "CHANGELOG.md").exists()


def test_contributing_exists():
    root = Path(__file__).parent.parent
    assert (root / "CONTRIBUTING.md").exists()


def test_security_doc_exists():
    root = Path(__file__).parent.parent
    assert (root / "SECURITY.md").exists()


def test_architecture_doc_exists():
    root = Path(__file__).parent.parent
    assert (root / "ARCHITECTURE.md").exists()


def test_mkdocs_config_exists():
    root = Path(__file__).parent.parent
    assert (root / "mkdocs.yml").exists()


def test_docs_index_exists():
    root = Path(__file__).parent.parent
    assert (root / "docs" / "index.md").exists()


def test_gitignore_has_coverage():
    root = Path(__file__).parent.parent
    content = (root / ".gitignore").read_text()
    assert "htmlcov" in content
    assert ".coverage" in content


def test_editorconfig_exists():
    root = Path(__file__).parent.parent
    assert (root / ".editorconfig").exists()


def test_precommit_config_exists():
    root = Path(__file__).parent.parent
    assert (root / ".pre-commit-config.yaml").exists()
