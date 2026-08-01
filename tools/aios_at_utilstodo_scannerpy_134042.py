#!/usr/bin/env python3
"""
Utility module for scanning TODO-like tags in Python source files.

This module provides a single public function :func:`scan_todos` that
recursively walks a directory tree and returns all occurrences of
specified tags (e.g. ``TODO``, ``FIXME``) found in Python files.

The module is self‑contained and can be executed directly to run a
simple test harness that demonstrates its functionality.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Iterable, List, Tuple

__all__ = ["TODO_TAGS", "scan_todos"]


# Default tags to search for in source files.
TODO_TAGS: List[str] = ["TODO", "FIXME", "HACK", "XXX", "BUG"]


def scan_todos(
    root_dir: str,
    tags: Iterable[str] | None = None,
) -> List[Tuple[str, int, str, str]]:
    """
    Recursively scan Python files under *root_dir* for lines containing any
    of the specified tags.

    Parameters
    ----------
    root_dir : str
        The directory to start scanning from.
    tags : Iterable[str] | None, optional
        A collection of tags to look for. If ``None`` (default), the
        module's :data:`TODO_TAGS` are used.

    Returns
    -------
    List[Tuple[str, int, str, str]]
        A list of tuples in the form ``(file_path, line_number, tag,
        line_text)`` for each match found.

    Notes
    -----
    Files that cannot be opened or decoded are silently skipped.
    """
    if tags is None:
        tags = TODO_TAGS

    # Build a regex that matches any of the tags as whole words.
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, tags)) + r")\b")

    results: List[Tuple[str, int, str, str]] = []

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue

            file_path = os.path.join(dirpath, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for lineno, line in enumerate(f, start=1):
                        match = pattern.search(line)
                        if match:
                            results.append(
                                (file_path, lineno, match.group(0), line.strip())
                            )
            except (OSError, UnicodeDecodeError):
                # Skip files that cannot be read or decoded.
                continue

    return results


if __name__ == "__main__":
    # Simple test harness that creates a temporary directory with
    # sample Python files containing TODO tags and prints the scan
    # results.

    with tempfile.TemporaryDirectory() as tmpdir:
        sample_file = Path(tmpdir) / "sample.py"
        sample_file.write_text(
            """\
# Sample Python file
def foo():
    pass  # TODO: implement this function

# FIXME: this is a placeholder
""",
            encoding="utf-8",
        )

        print(f"Scanning temporary directory: {tmpdir}")
        found = scan_todos(tmpdir)
        if found:
            print("Found the following TODO-like tags:")
            for file_path, line_no, tag, text in found:
                print(f"{file_path}:{line_no} [{tag}] {text}")
        else:
            print("No TODO-like tags found.")