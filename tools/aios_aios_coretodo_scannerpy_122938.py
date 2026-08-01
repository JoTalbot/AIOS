#!/usr/bin/env python3
"""
aios_core.todo_scanner

Utility module for scanning Python source files for TODO, FIXME, HACK, XXX, and BUG tags.

The :func:`scan_todos` function walks a directory tree and returns a list of
strings in the format ``"{file_path}:{line_no}:{tag}:{text}"`` for each
occurrence of a tag in a Python file.

This module is intended to be imported by other parts of the project (e.g.
``run_coder_orchestrator``) to replace duplicated inline scanning logic.
"""

from __future__ import annotations

import os
import re
from typing import List

__all__ = ["TAGS", "TAG_RE", "scan_todos"]

# --------------------------------------------------------------------------- #
# Tag definitions
# --------------------------------------------------------------------------- #
TAGS: List[str] = ["TODO", "FIXME", "HACK", "XXX", "BUG"]
TAG_RE: re.Pattern[str] = re.compile(r"\b(" + "|".join(TAGS) + r")\b")

# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def scan_todos(directory: str) -> List[str]:
    """
    Scan all ``.py`` files under *directory* for TODO/FIXME/HACK/XXX/BUG tags.

    Parameters
    ----------
    directory : str
        Path to the root directory to scan.

    Returns
    -------
    List[str]
        A list of strings in the format
        ``"{file_path}:{line_no}:{tag}:{text}"`` for each tag found.

    Notes
    -----
    Files that cannot be opened or decoded are silently skipped.
    """
    todos: List[str] = []

    for root, _, files in os.walk(directory):
        for filename in files:
            if not filename.endswith(".py"):
                continue

            path = os.path.join(root, filename)

            try:
                with open(path, "r", encoding="utf-8") as fh:
                    for lineno, line in enumerate(fh, 1):
                        for match in TAG_RE.finditer(line):
                            tag = match.group(0)
                            text = line[match.end() :].strip()
                            todos.append(f"{path}:{lineno}:{tag}:{text}")
            except (OSError, UnicodeDecodeError):
                # Skip files that cannot be read
                continue

    return todos

# --------------------------------------------------------------------------- #
# Self‑test
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Scan a directory for TODO/FIXME/HACK/XXX/BUG tags."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Root directory to scan (default: current directory)",
    )
    args = parser.parse_args()

    results = scan_todos(args.directory)
    if results:
        print("\n".join(results))
    else:
        print("No tags found.", file=sys.stderr)
        sys.exit(1)