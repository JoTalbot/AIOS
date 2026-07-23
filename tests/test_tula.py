"""Tests for the AIOS Constitutional Tool ('tula')."""

from pathlib import Path

import pytest

from tools.complete_constitution_tula import (
    generate_compliance_matrix,
    generate_index,
    generate_report,
    parse_article_file,
    scan_constitution,
)


def test_scan_constitution_exists():
    constitution_dir = Path(__file__).parent.parent / "docs" / "constitution"
    articles = scan_constitution(constitution_dir)
    assert len(articles) == 67
    for i in range(1, 68):
        assert i in articles
        assert articles[i]["valid"] is True


def test_parse_single_article(tmp_path):
    art_file = tmp_path / "ARTICLE-I-TEST.md"
    art_file.write_text(
        """# Article I — Test Identity

Status: Core
Level: Constitutional
Scope: System-wide

# Principle
Everything must have identity.

Laws:
1. ID must be unique.
""",
        encoding="utf-8",
    )

    parsed = parse_article_file(art_file)
    assert parsed["number"] == 1
    assert parsed["numeral"] == "I"
    assert parsed["valid"] is True


def test_report_generation(tmp_path):
    constitution_dir = Path(__file__).parent.parent / "docs" / "constitution"
    articles = scan_constitution(constitution_dir)
    report_file = tmp_path / "CONSTITUTION_REPORT.md"
    generate_report(articles, report_file)

    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "Compliance Ratio:** 100.00%" in content
    assert "LXVII" in content


def test_matrix_and_index(tmp_path):
    matrix_file = tmp_path / "COMPLIANCE_MATRIX.md"
    generate_compliance_matrix(matrix_file)
    assert matrix_file.exists()
    assert "100% Constitutional Coverage" in matrix_file.read_text(encoding="utf-8")

    index_file = tmp_path / "INDEX.md"
    constitution_dir = Path(__file__).parent.parent / "docs" / "constitution"
    articles = scan_constitution(constitution_dir)
    generate_index(articles, index_file)
    assert index_file.exists()
    assert "Master Constitution Index" in index_file.read_text(encoding="utf-8")
