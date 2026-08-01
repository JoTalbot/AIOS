"""
todo_scanner.py

A small utility module that scans a Python source file for common
TODO‑style markers using the abstract syntax tree (AST).  It
returns a list of tuples containing the line number, the matched
tag, and the full line of source code.

The module is intentionally lightweight and self‑contained so it can
be imported from other parts of the project without side effects.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Tuple

__all__ = ["scan_file_for_todos"]


def _extract_tags(value: str) -> List[str]:
    """
    Return a list of TODO tags found in *value*.

    The tags are case‑sensitive and include:
    - TODO
    - FIXME
    - HACK
    - XXX
    - BUG
    """
    tags = ["TODO", "FIXME", "HACK", "XXX", "BUG"]
    return [tag for tag in tags if tag in value]


def scan_file_for_todos(path: str) -> List[Tuple[int, str, str]]:
    """
    Scan a Python file for TODO‑style markers.

    Parameters
    ----------
    path : str
        Path to the Python source file to scan.

    Returns
    -------
    List[Tuple[int, str, str]]
        A list of tuples, each containing:
        - line number (int)
        - matched tag (str)
        - full line text (str)

    Notes
    -----
    * The file is opened with UTF‑8 encoding and ``errors='replace'`` to
      avoid crashes on bad encodings.
    * If the file cannot be parsed as valid Python, an empty list is
      returned.
    """
    try:
        source = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        # File cannot be read; return empty list
        return []

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        # Parsing failed; return empty list
        return []

    # Split source into lines for quick lookup by line number
    lines = source.splitlines()

    todos: List[Tuple[int, str, str]] = []

    for node in ast.walk(tree):
        # Handle string literals in different AST node types
        if isinstance(node, ast.Str):  # pragma: no cover (Python <3.8)
            value = node.s
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
        else:
            continue

        tags = _extract_tags(value)
        if not tags:
            continue

        # Retrieve the full line text; guard against out‑of‑range indices
        line_no = getattr(node, "lineno", None)
        if line_no is None or line_no < 1 or line_no > len(lines):
            continue
        full_line = lines[line_no - 1]

        for tag in tags:
            todos.append((line_no, tag, full_line))

    return todos


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Scan a Python file for TODO markers."
    )
    parser.add_argument(
        "file",
        type=str,
        help="Path to the Python source file to scan",
    )
    args = parser.parse_args()

    results = scan_file_for_todos(args.file)
    if not results:
        print("No TODO markers found.")
        sys.exit(0)

    print(f"Found {len(results)} TODO marker(s) in {args.file}:")
    for line_no, tag, line_text in results:
        print(f"{line_no:4d}: [{tag}] {line_text}")