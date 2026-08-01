# todo_scanner.py
"""
Utility module for scanning Python source files for TODO‑style comments.

The :func:`scan_todos` function walks through all ``.py`` files under a given
directory, extracts lines containing any of the tags
``['TODO', 'FIXME', 'HACK', 'XXX', 'BUG']`` and returns a list of tuples
``(file_path, line_number, line_text)``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Tuple

__all__ = ["scan_todos"]


def scan_todos(root_dir: str) -> List[Tuple[str, int, str]]:
    """
    Recursively scan ``root_dir`` for Python files and collect lines that
    contain TODO‑style tags.

    Parameters
    ----------
    root_dir : str
        Path to the directory to scan.

    Returns
    -------
    List[Tuple[str, int, str]]
        A list of tuples where each tuple contains:
        * ``file_path`` – absolute path to the file containing the tag
        * ``line_number`` – 1‑based line number of the tag
        * ``line_text`` – the full line text (stripped of trailing newline)

    Notes
    -----
    * Files that cannot be read (e.g. due to permissions) are silently
      skipped.
    * The function is case‑sensitive; only the exact tags listed are
      recognised.
    """
    tags = {"TODO", "FIXME", "HACK", "XXX", "BUG"}
    tag_pattern = re.compile(r"\b(" + "|".join(tags) + r")\b")
    results: List[Tuple[str, int, str]] = []

    root_path = Path(root_dir).resolve()
    if not root_path.is_dir():
        raise ValueError(f"Provided root_dir '{root_dir}' is not a directory")

    for py_file in root_path.rglob("*.py"):
        try:
            with py_file.open(encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    if tag_pattern.search(line):
                        results.append((str(py_file), lineno, line.rstrip("\n")))
        except (OSError, UnicodeDecodeError) as exc:
            # Skip files that cannot be read; log the error if needed
            # For now we simply ignore them to keep the function robust.
            # In a real project you might want to log this exception.
            continue

    return results


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Scan a directory for TODO tags.")
    parser.add_argument(
        "root",
        nargs="?",
        default=os.getcwd(),
        help="Root directory to scan (default: current working directory)",
    )
    args = parser.parse_args()

    todos = scan_todos(args.root)
    print(json.dumps(todos, indent=2))