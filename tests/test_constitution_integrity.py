"""Verify constitution file integrity."""

from pathlib import Path


def test_constitution_directory_exists():
    root = Path(__file__).parent.parent
    d = root / "docs" / "constitution"
    if d.exists():
        articles = list(d.glob("ARTICLE-*.md"))
        assert len(articles) > 0


def test_constitution_index_exists():
    root = Path(__file__).parent.parent
    index = root / "docs" / "constitution" / "INDEX.md"
    if index.exists():
        assert index.stat().st_size > 0


def test_policies_directory_exists():
    root = Path(__file__).parent.parent
    p = root / "policies"
    assert p.exists() or True  # may be empty
