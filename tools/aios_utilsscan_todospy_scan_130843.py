# File: utils/scan_todos.py
"""
Utility module for scanning Python files for TODO, FIXME, and HACK comments.

The :func:`scan_for_todos` function walks a directory tree, reads all `.py` files,
and returns a list of tuples containing the file path, line number, and the
comment text following the keyword.

Example usage:
    >>> todos = scan_for_todos(os.getcwd())
    >>> for file_path, line_no, comment in todos:
    ...     print(f"{file_path}:{line_no} -> {comment}")
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Tuple

__all__ = ["scan_for_todos"]


def scan_for_todos(root_path: str) -> List[Tuple[str, int, str]]:
    """
    Scan the directory tree rooted at ``root_path`` for TODO, FIXME, and HACK comments.

    Parameters
    ----------
    root_path : str
        The root directory to start scanning from.

    Returns
    -------
    List[Tuple[str, int, str]]
        A list of tuples where each tuple contains:
        - The absolute file path of the Python file.
        - The line number (1-indexed) where the comment was found.
        - The comment text following the keyword (including the keyword).
    """
    todo_pattern = re.compile(r"#\s*(TODO|FIXME|HACK)\b.*", re.IGNORECASE)
    results: List[Tuple[str, int, str]] = []

    for dirpath, _, filenames in os.walk(root_path):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            file_path = Path(dirpath) / filename
            try:
                with file_path.open(encoding="utf-8") as f:
                    for line_no, line in enumerate(f, start=1):
                        match = todo_pattern.search(line)
                        if match:
                            # Extract the full comment text after the keyword
                            comment_text = line[match.start() :].strip()
                            results.append((str(file_path.resolve()), line_no, comment_text))
            except (OSError, UnicodeDecodeError) as exc:
                # Skip files that cannot be read; log the error if needed
                # For this utility, we silently ignore unreadable files.
                continue

    return results


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Scan for TODO/FIXME/HACK comments.")
    parser.add_argument(
        "path",
        nargs="?",
        default=os.getcwd(),
        help="Root directory to scan (default: current working directory)",
    )
    args = parser.parse_args()

    todos = scan_for_todos(args.path)
    if not todos:
        print("No TODO/FIXME/HACK comments found.")
        sys.exit(0)

    for file_path, line_no, comment in todos:
        print(f"{file_path}:{line_no} -> {comment}")