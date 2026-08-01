# tools/aios_udalite_blок_kода_123856.py
"""
Module to scan a project for TODO, FIXME, HACK, XXX, and BUG tags using
the external `scan_todos` function from `todo_scanner`.
"""

from __future__ import annotations

import os
from typing import List, Dict, Any

# Import the external scanner
from todo_scanner import scan_todos

__all__ = ["main", "scan_todos"]


def main(project_root: str | None = None) -> None:
    """
    Scan the given project root for TODO-like tags and print a report.

    Parameters
    ----------
    project_root : str | None
        Path to the project root. If None, the current working directory
        is used.
    """
    root = project_root or os.getcwd()
    tags = ["TODO", "FIXME", "HACK", "XXX", "BUG"]
    try:
        todos: List[Dict[str, Any]] = scan_todos(root, tags=tags)
    except Exception as exc:  # pragma: no cover
        print(f"Error scanning TODOs: {exc}")
        return

    if not todos:
        print("No TODO-like tags found.")
        return

    print("TODO Report:")
    for todo in todos:
        file_path = todo.get("file", "<unknown>")
        line_no = todo.get("line", 0)
        tag = todo.get("tag", "<unknown>")
        text = todo.get("text", "").strip()
        print(f"{file_path}:{line_no} [{tag}] {text}")


if __name__ == "__main__":  # pragma: no cover
    main()