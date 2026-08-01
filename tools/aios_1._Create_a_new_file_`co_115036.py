# code_scanner.py
"""
Utility module for scanning source files for specific tags such as TODO or BUG.

The module provides two main functions:
    * :func:`scan_file_for_tags` – scans a single file for the supplied tags.
    * :func:`scan_directory_for_tags` – recursively scans a directory tree,
      skipping hidden files and directories, and aggregates the results per file.

Both functions are fully type‑annotated, documented, and handle decoding errors
gracefully by falling back to ``errors='replace'`` when UTF‑8 decoding fails.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

__all__ = ["scan_file_for_tags", "scan_directory_for_tags"]


def _open_file_with_fallback(file_path: Path) -> List[str]:
    """
    Open a file using UTF‑8 encoding. If a :class:`UnicodeDecodeError` occurs,
    reopen the file with ``errors='replace'`` to avoid crashes.

    Parameters
    ----------
    file_path : Path
        Path to the file to be opened.

    Returns
    -------
    List[str]
        List of lines read from the file.
    """
    try:
        with file_path.open(encoding="utf-8", errors="strict") as f:
            return f.readlines()
    except UnicodeDecodeError:
        with file_path.open(encoding="utf-8", errors="replace") as f:
            return f.readlines()


def scan_file_for_tags(file_path: str, tags: Iterable[str]) -> List[Tuple[int, str, str]]:
    """
    Scan a single file for occurrences of any of the supplied tags.

    Parameters
    ----------
    file_path : str
        Path to the file to scan.
    tags : Iterable[str]
        Iterable of tag strings to search for (e.g. ``["TODO", "BUG"]``).

    Returns
    -------
    List[Tuple[int, str, str]]
        A list of tuples ``(line_number, tag, line_text)`` for each match.
        ``line_number`` is 1‑based.
    """
    path = Path(file_path)
    lines = _open_file_with_fallback(path)
    results: List[Tuple[int, str, str]] = []

    for idx, line in enumerate(lines, start=1):
        for tag in tags:
            if tag in line:
                results.append((idx, tag, line.rstrip("\n")))
    return results


def scan_directory_for_tags(directory: str, tags: Iterable[str]) -> Dict[str, List[Tuple[int, str, str]]]:
    """
    Recursively scan a directory tree for files containing any of the supplied tags.

    Hidden files and directories (those starting with a dot) are skipped.

    Parameters
    ----------
    directory : str
        Root directory to start scanning from.
    tags : Iterable[str]
        Iterable of tag strings to search for.

    Returns
    -------
    Dict[str, List[Tuple[int, str, str]]]
        Mapping from relative file path to a list of tag matches.
    """
    root = Path(directory).resolve()
    results: Dict[str, List[Tuple[int, str, str]]] = {}

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]

        for filename in filenames:
            if filename.startswith("."):
                continue  # skip hidden files
            file_path = Path(dirpath) / filename
            rel_path = str(file_path.relative_to(root))
            tags_in_file = scan_file_for_tags(str(file_path), tags)
            if tags_in_file:
                results[rel_path] = tags_in_file

    return results


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Scan files for TODO/BUG tags.")
    parser.add_argument("path", help="File or directory to scan")
    parser.add_argument(
        "-t",
        "--tags",
        nargs="+",
        default=["TODO", "BUG"],
        help="Tags to search for (default: TODO BUG)",
    )
    args = parser.parse_args()

    if Path(args.path).is_dir():
        output = scan_directory_for_tags(args.path, args.tags)
    else:
        output = {args.path: scan_file_for_tags(args.path, args.tags)}

    print(json.dumps(output, indent=2, ensure_ascii=False))