#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
aios_core.todo_scanner

This module provides a simple utility to scan Python source files for
common TODO-like tags such as ``TODO``, ``FIXME``, ``HACK``, ``XXX`` and
``BUG``.  The :func:`scan_for_todos` function returns a list of tuples
containing the file path, line number and the matched tag text.

The module is intentionally lightweight and self‑contained so it can be
imported from other parts of the project (e.g. ``run_coder_orchestrator``)
without pulling in any heavy dependencies.
"""

from __future__ import annotations

import pathlib
import re
from typing import List, Tuple

__all__ = ["scan_for_todos", "TODO_TAGS", "TODO_PATTERN"]


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

TODO_TAGS: List[str] = ["TODO", "FIXME", "HACK", "XXX", "BUG"]
TODO_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:" + "|".join(map(re.escape, TODO_TAGS)) + r")\b:?(.*)"
)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def scan_for_todos(paths: List[pathlib.Path]) -> List[Tuple[pathlib.Path, int, str]]:
    """
    Scan a list of file paths for TODO-like tags.

    Parameters
    ----------
    paths : List[pathlib.Path]
        A list of file system paths to inspect.

    Returns
    -------
    List[Tuple[pathlib.Path, int, str]]
        A list of tuples where each tuple contains:
        * the file path,
        * the line number (1‑based),
        * the matched tag text (including the tag and any trailing message).

    Notes
    -----
    * Only files with a ``.py`` suffix are considered.
    * Files that cannot be opened (e.g. due to permissions) are silently
      skipped; an error message is printed to ``stderr``.
    """
    results: List[Tuple[pathlib.Path, int, str]] = []

    for path in paths:
        if not path.is_file() or path.suffix != ".py":
            continue

        try:
            with path.open("r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    match = TODO_PATTERN.search(line)
                    if match:
                        # ``match.group(0)`` contains the full matched text
                        results.append((path, lineno, match.group(0).strip()))
        except (OSError, UnicodeDecodeError) as exc:
            # Gracefully skip unreadable files; log the issue.
            print(f"Warning: could not read {path!s}: {exc}", file=sys.stderr)

    return results


# --------------------------------------------------------------------------- #
# Self‑test
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import sys
    import tempfile

    # Create a temporary Python file containing a few TODO tags
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(
            """# Sample file
def foo():
    pass  # TODO: implement this function
# FIXME: this is a known issue
# No tag here
# HACK: quick fix
"""
        )
        tmp_path = pathlib.Path(tmp.name)

    # Scan the temporary file
    found = scan_for_todos([tmp_path])

    # Print results
    print("Found TODO tags:")
    for file_path, line_no, text in found:
        print(f"{file_path}:{line_no}: {text}")

    # Clean up the temporary file
    try:
        tmp_path.unlink()
    except OSError:
        pass