#!/usr/bin/env python3
"""
aios_utilstodo_scannerpy_inside_134618.py

This module provides a utility function to scan Python source files for
common issue tags such as ``TODO``, ``FIXME``, ``HACK``, ``XXX`` and ``BUG``.
The function walks through all ``.py`` files under a given root directory
and returns a list of tuples containing the file path, line number,
and the line content for each match.

The module is self‑contained, includes type hints, a comprehensive
docstring, and a small test harness that can be executed directly.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple

__all__ = ["scan_todo_in_files"]


def scan_todo_in_files(root_dir: str) -> List[Tuple[str, int, str]]:
    """
    Walk through all ``.py`` files under ``root_dir`` and collect lines
    that contain any of the issue tags: ``TODO``, ``FIXME``, ``HACK``,
    ``XXX`` or ``BUG``.

    Parameters
    ----------
    root_dir : str
        The root directory to start scanning from.

    Returns
    -------
    List[Tuple[str, int, str]]
        A list of tuples where each tuple contains:
        - The absolute file path as a string.
        - The 1‑based line number where the tag was found.
        - The full line content (including the newline character).

    Notes
    -----
    * The search is case‑sensitive.
    * Lines are read in text mode using the default system encoding.
    * If ``root_dir`` does not exist or is not a directory, an empty list
      is returned.
    """
    tags = {"TODO", "FIXME", "HACK", "XXX", "BUG"}
    results: List[Tuple[str, int, str]] = []

    root_path = Path(root_dir).resolve()
    if not root_path.is_dir():
        return results

    for py_file in root_path.rglob("*.py"):
        try:
            with py_file.open(encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    if any(tag in line for tag in tags):
                        results.append((str(py_file), lineno, line.rstrip("\n")))
        except (OSError, UnicodeDecodeError) as exc:
            # Skip files that cannot be read; log the error if needed.
            # For this module we silently ignore such files.
            continue

    return results


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Scan a directory for TODO/FIXME/HACK/XXX/BUG tags."
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Root directory to scan (default: current directory)",
    )
    args = parser.parse_args()

    matches = scan_todo_in_files(args.root)
    if not matches:
        print("No tags found.")
        sys.exit(0)

    print(f"Found {len(matches)} tag(s):")
    for file_path, line_no, line_content in matches:
        print(f"{file_path}:{line_no}: {line_content}")

    sys.exit(1)