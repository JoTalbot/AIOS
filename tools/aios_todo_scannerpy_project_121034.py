#!/usr/bin/env python3
"""
aios_todo_scannerpy_project_121034.py

A lightweight utility to scan Python source files for common TODO-like tags
(`TODO`, `FIXME`, `HACK`, `XXX`, `BUG`).  The :func:`scan_todos` function
recursively walks a directory tree, collects all matches, and returns a
structured dictionary.

The module is intentionally self‑contained and can be imported by other
scripts (e.g. ``run_coder_orchestrator.py``) or executed directly for
quick checks.

Usage
-----
>>> from aios_todo_scannerpy_project_121034 import scan_todos
>>> results = scan_todos('.')
>>> for file, entries in results.items():
...     for entry in entries:
...         print(f"{file}:{entry['line_number']} {entry['tag']} - {entry['line_text'].strip()}")
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List

__all__ = ["scan_todos"]


def scan_todos(root_dir: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Recursively scan ``root_dir`` for Python files and collect all occurrences
    of the tags ``TODO``, ``FIXME``, ``HACK``, ``XXX``, and ``BUG``.

    Parameters
    ----------
    root_dir : str
        The root directory to start the search from.

    Returns
    -------
    Dict[str, List[Dict[str, Any]]]
        A mapping from absolute file paths to a list of dictionaries, each
        representing a found tag with keys:
        - ``line_number`` (int): The 1‑based line number.
        - ``line_text`` (str): The raw line text.
        - ``tag`` (str): The matched tag.

    Notes
    -----
    The function is tolerant to file read errors; such files are skipped
    and a warning is printed to ``stderr``.
    """
    tag_pattern = re.compile(r"\b(TODO|FIXME|HACK|XXX|BUG)\b")
    results: Dict[str, List[Dict[str, Any]]] = {}

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue

            file_path = Path(dirpath) / filename
            try:
                with file_path.open(encoding="utf-8") as f:
                    for line_number, line in enumerate(f, start=1):
                        match = tag_pattern.search(line)
                        if match:
                            entry: Dict[str, Any] = {
                                "line_number": line_number,
                                "line_text": line.rstrip("\n"),
                                "tag": match.group(0),
                            }
                            results.setdefault(str(file_path), []).append(entry)
            except (OSError, UnicodeDecodeError) as exc:
                # Gracefully skip unreadable files
                print(f"Warning: Skipping {file_path} due to {exc!s}", file=sys.stderr)

    return results


if __name__ == "__main__":
    import json
    import sys

    root = sys.argv[1] if len(sys.argv) > 1 else "."
    todos = scan_todos(root)

    if todos:
        print(json.dumps(todos, indent=2))
        sys.exit(1)
    else:
        print("No TODO-like tags found.")
        sys.exit(0)