"""Tests for tech_debt_reporter module"""
import tempfile
import pathlib
import json
from aios_core.tech_debt_reporter import TechDebtReporter, DebtItem

def test_scan_todos(tmp_path):
    # Create temp py file with TODOs
    test_file = tmp_path / "test.py"
    test_file.write_text("""
# TODO: fix this
def foo():
    pass # FIXME: broken
    x = 1 # HACK temporary
""")
    reporter = TechDebtReporter(repo_path=str(tmp_path))
    items = reporter.scan_todos()
    assert len(items) >= 2
    types = [i.type for i in items]
    assert "TODO" in types or "FIXME" in types

def test_generate_report():
    reporter = TechDebtReporter(repo_path=".")
    report = reporter.generate_report()
    assert "summary" in report
    assert "todos" in report
    assert "complexity_hotspots" in report
    assert "security" in report
    assert report["summary"]["total_todos"] >= 0

def test_save_json(tmp_path):
    reporter = TechDebtReporter(repo_path=".")
    out_path, report = reporter.save_json(output_path=str(tmp_path / "report.json"))
    assert pathlib.Path(out_path).exists()
    data = json.loads(pathlib.Path(out_path).read_text())
    assert "summary" in data

def test_debt_item_dataclass():
    item = DebtItem(file="a.py", line=10, type="TODO", content="fix me")
    assert item.file == "a.py"
    assert item.severity == "medium"
