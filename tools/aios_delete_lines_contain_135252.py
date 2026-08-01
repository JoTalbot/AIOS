#!/usr/bin/env python3
"""
aios_delete_lines_contain_135252.py

This module provides a utility function to recursively scan a directory for
Python source files and extract lines that contain any of the following
tags: TODO, FIXME, HACK, XXX, BUG.

The function is designed to replace an older inline scanning logic that
was duplicated in the orchestrator. It returns a list of tuples
containing the file path, line number, and the matched line.

The module also includes a simple test harness that can be executed
directly to verify its behaviour.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

__all__ = ["scan_todos"]


def scan_todos(root_dir: Path) -> List[Tuple[Path, int, str]]:
    """
    Recursively scan ``root_dir`` for Python files and return a list of
    tuples describing lines that contain TODO, FIXME, HACK, XXX, or BUG tags.

    Parameters
    ----------
    root_dir : Path
        The directory to start the recursive search from.

    Returns
    -------
    List[Tuple[Path, int, str]]
        A list where each element is a tuple of:
        - Path to the file containing the tag
        - Line number (1‑based) where the tag appears
        - The full line text (stripped of trailing newline)

    Notes
    -----
    The function is tolerant to file read errors; any file that cannot be
    opened or decoded is skipped with a warning printed to stderr.
    """
    # Compile a regex that matches any of the tags as whole words, case‑sensitive.
    tag_pattern = re.compile(r"\b(TODO|FIXME|HACK|XXX|BUG)\b")

    todos: List[Tuple[Path, int, str]] = []

    for file_path in root_dir.rglob("*.py"):
        try:
            with file_path.open(encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    if tag_pattern.search(line):
                        todos.append((file_path, line_no, line.rstrip("\n")))
        except (OSError, UnicodeDecodeError) as exc:
            # Gracefully skip files that cannot be read.
            print(f"Warning: Skipping {file_path} due to {exc!s}", file=sys.stderr)

    return todos


if __name__ == "__main__":
    import sys

    # Determine the root directory: default to the directory containing this script.
    root = Path(__file__).parent

    # If a path is provided as a command‑line argument, use it instead.
    if len(sys.argv) > 1:
        root = Path(sys.argv[1]).expanduser().resolve()

    print(f"Scanning for TODO/FIXME/HACK tags in {root} ...")
    results = scan_todos(root)

    if not results:
        print("No tags found.")
    else:
        for file_path, line_no, line_text in results:
            print(f"{file_path}:{line_no}: {line_text}")