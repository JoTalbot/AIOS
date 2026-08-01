#!/usr/bin/env python3
"""
tools/aios_helper_named_scan_132037.py

A self‑contained helper module that scans Python source files for
common development tags such as TODO, FIXME, HACK, XXX, and BUG.

The module exposes a single public function:

    scan_for_todo_in_files(base_dir: str) -> List[Tuple[str, int, str]]

which returns a list of tuples containing the file path, line number,
and the line text for every line that contains any of the tags.

The module also provides a simple command‑line interface for quick
manual testing.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Tuple

__all__ = ["scan_for_todo_in_files"]


# Tags to look for in source files
_TAGS: Tuple[str, ...] = ("TODO", "FIXME", "HACK", "XXX", "BUG")


def scan_for_todo_in_files(base_dir: str) -> List[Tuple[str, int, str]]:
    """
    Walk through all ``.py`` files under ``base_dir`` and collect
    lines that contain any of the predefined tags.

    Parameters
    ----------
    base_dir : str
        The root directory to start scanning from.

    Returns
    -------
    List[Tuple[str, int, str]]
        A list of tuples, each containing:
        - The absolute file path as a string.
        - The line number (1‑based) where the tag was found.
        - The stripped line text that contains the tag.

    Notes
    -----
    * The search is case‑sensitive; tags must match exactly as defined
      in :data:`_TAGS`.
    * Files that cannot be opened (e.g. due to permissions) are
      skipped with an error message printed to ``stderr``.
    """
    todos: List[Tuple[str, int, str]] = []

    base_path = Path(base_dir).resolve()
    if not base_path.is_dir():
        print(f"Error: '{base_dir}' is not a directory.", file=sys.stderr)
        return todos

    for file_path in base_path.rglob("*.py"):
        try:
            with file_path.open(encoding="utf-8", errors="ignore") as fp:
                for line_number, line in enumerate(fp, start=1):
                    if any(tag in line for tag in _TAGS):
                        todos.append((str(file_path), line_number, line.strip()))
        except OSError as exc:
            print(
                f"Warning: Could not read '{file_path}': {exc}",
                file=sys.stderr,
            )

    return todos


if __name__ == "__main__":
    # Simple command‑line interface for quick manual testing
    import argparse

    parser = argparse.ArgumentParser(
        description="Scan Python files for TODO/FIXME/HACK/XXX/BUG tags."
    )
    parser.add_argument(
        "base_dir",
        nargs="?",
        default=".",
        help="Base directory to scan (default: current directory)",
    )
    args = parser.parse_args()

    results = scan_for_todo_in_files(args.base_dir)
    if not results:
        print("No tags found.")
    else:
        for file_path, line_no, line_text in results:
            print(f"{file_path}:{line_no}: {line_text}")