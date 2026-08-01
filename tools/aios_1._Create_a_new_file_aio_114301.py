# File: aios_core/utils/scan_todo.py
"""
Utility module for scanning TODO-like tags in Python projects.

Provides :func:`scan_todo_in_project` which walks through all ``.py`` files
under a given root directory and extracts occurrences of the tags
``TODO``, ``FIXME``, ``HACK``, ``XXX`` and ``BUG``.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

__all__ = ["scan_todo_in_project"]

logger = logging.getLogger(__name__)

_TAG_PATTERN = re.compile(r"\b(TODO|FIXME|HACK|XXX|BUG)\b")


def scan_todo_in_project(root_path: Path) -> List[Dict[str, Any]]:
    """
    Scan all Python files under *root_path* for TODO-like tags.

    Parameters
    ----------
    root_path : Path
        The root directory to start scanning from.

    Returns
    -------
    List[Dict[str, Any]]
        A list of dictionaries, each containing:
        - ``file_path`` (str): Absolute path to the file.
        - ``line_number`` (int): 1‑based line number where the tag was found.
        - ``tag`` (str): The matched tag.
        - ``line_text`` (str): The full line of text (stripped of trailing whitespace).

    Notes
    -----
    The function is tolerant to file read errors; any file that cannot be
    opened will be skipped with a warning logged.
    """
    results: List[Dict[str, Any]] = []

    if not root_path.is_dir():
        logger.warning("Provided root_path %s is not a directory.", root_path)
        return results

    for py_file in root_path.rglob("*.py"):
        try:
            with py_file.open(encoding="utf-8") as f:
                for line_number, line in enumerate(f, start=1):
                    match = _TAG_PATTERN.search(line)
                    if match:
                        results.append(
                            {
                                "file_path": str(py_file.resolve()),
                                "line_number": line_number,
                                "tag": match.group(1),
                                "line_text": line.rstrip("\n"),
                            }
                        )
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning(
                "Could not read file %s: %s", py_file, exc, exc_info=exc
            )
    return results


if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    # Simple demo: create a temporary project with a few tags
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "module1.py").write_text(
            "def foo():\n    pass  # TODO: implement\n"
        )
        (tmp_path / "module2.py").write_text(
            "# FIXME: this is broken\n"
        )
        report = scan_todo_in_project(tmp_path)
        print(json.dumps(report, indent=2))


# File: aios_core/utils/__init__.py
"""
Utility subpackage for aios_core.
"""

from .scan_todo import scan_todo_in_project

__all__ = ["scan_todo_in_project"]


# File: run_coder_orchestrator.py
"""
Orchestrator for running code analysis and reporting technical debt.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from aios_core.utils import scan_todo_in_project

logger = logging.getLogger(__name__)

def main() -> None:
    """
    Main entry point for the orchestrator.

    Scans the current working directory for Python files,
    then scans for TODO-like tags and logs a structured report.
    """
    root = Path.cwd()
    logger.info("Starting project scan in %s", root)

    # Placeholder for the original project scan logic.
    # ...

    # Scan for technical debt tags
    technical_debt_report = scan_todo_in_project(root)

    # Log the report as a JSON array
    logger.info(
        "Technical debt report:\n%s",
        json.dumps(technical_debt_report, indent=2),
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()


# File: tests/test_scan_todo.py
"""
Unit tests for the scan_todo_in_project function.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any

import pytest

from aios_core.utils import scan_todo_in_project


@pytest.fixture
def temp_project(tmp_path_factory) -> Path:
    """
    Create a temporary project directory with sample Python files.
    """
    root = tmp_path_factory.mktemp("project")
    (root / "a.py").write_text(
        "def a():\n    pass  # TODO: implement a\n"
        "# FIXME: something wrong\n"
    )
    (root / "b.py").write_text(
        "def b():\n    pass  # HACK: temporary\n"
    )
    (root / "c.py").write_text(
        "def c():\n    pass\n"
    )
    return root


def test_scan_todo_in_project(temp_project: Path) -> None:
    """
    Verify that scan_todo_in_project correctly identifies tags.
    """
    report: List[Dict[str, Any]] = scan_todo_in_project(temp_project)

    # Expected entries
    expected = [
        {
            "file_path": str((temp_project / "a.py").resolve()),
            "line_number": 2,
            "tag": "TODO",
            "line_text": "    pass  # TODO: implement a",
        },
        {
            "file_path": str((temp_project / "a.py").resolve()),
            "line_number": 3,
            "tag": "FIXME",
            "line_text": "# FIXME: something wrong",
        },
        {
            "file_path": str((temp_project / "b.py").resolve()),
            "line_number": 2,
            "tag": "HACK",
            "line_text": "    pass  # HACK: temporary",
        },
    ]

    # Sort both lists for comparison
    report_sorted = sorted(report, key=lambda d: (d["file_path"], d["line_number"]))
    expected_sorted = sorted(expected, key=lambda d: (d["file_path"], d["line_number"]))

    assert report_sorted == expected_sorted, (
        f"Expected {json.dumps(expected_sorted, indent=2)}\n"
        f"Got {json.dumps(report_sorted, indent=2)}"
    )