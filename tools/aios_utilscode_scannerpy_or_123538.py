"""
utils/code_scanner.py

A small utility module that scans a directory tree for Python source files
and extracts lines containing user‑defined tags such as ``TODO`` or ``FIXME``.

The main entry point is :func:`scan_for_tags`, which returns a list of
tuples containing the file path, line number, and the matched line.
The module is fully type‑annotated, follows PEP 8, and includes a
``__main__`` block for quick manual testing.

Example usage:

>>> from utils.code_scanner import scan_for_tags
>>> matches = scan_for_tags('src', ['TODO', 'FIXME'])
>>> for path, line_no, line in matches:
...     print(f'{path}:{line_no}: {line}')

"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

__all__ = ["scan_for_tags"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def scan_for_tags(path: str, tags: Iterable[str]) -> List[Tuple[str, int, str]]:
    """
    Walk the directory tree rooted at *path*, read each ``.py`` file,
    and return a list of tuples containing the file path, line number,
    and the matched line for every occurrence of any tag in *tags*.

    Parameters
    ----------
    path : str
        Root directory to start scanning from.
    tags : Iterable[str]
        Iterable of tag strings to search for (e.g. ``['TODO', 'FIXME']``).

    Returns
    -------
    List[Tuple[str, int, str]]
        A list of ``(file_path, line_number, line_text)`` tuples.
    """
    if not tags:
        logger.warning("No tags provided; returning empty list.")
        return []

    # Compile a regex that matches any of the tags as whole words.
    tag_pattern = re.compile(r"\b(?:{} )\b".format("|".join(map(re.escape, tags))))

    results: List[Tuple[str, int, str]] = []

    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        logger.error("Provided path '%s' is not a directory.", path)
        return results

    for py_file in root.rglob("*.py"):
        try:
            with py_file.open(encoding="utf-8", errors="ignore") as f:
                for line_no, line in enumerate(f, start=1):
                    if tag_pattern.search(line):
                        results.append((str(py_file), line_no, line.rstrip("\n")))
        except OSError as exc:
            logger.warning("Could not read file '%s': %s", py_file, exc)

    return results


if __name__ == "__main__":
    # Simple command‑line interface for quick testing.
    import argparse

    parser = argparse.ArgumentParser(description="Scan Python files for tags.")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Root directory to scan (default: current directory).",
    )
    parser.add_argument(
        "-t",
        "--tags",
        nargs="+",
        default=["TODO", "FIXME", "HACK", "XXX", "BUG"],
        help="List of tags to search for.",
    )
    args = parser.parse_args()

    matches = scan_for_tags(args.path, args.tags)
    if matches:
        for file_path, line_no, line in matches:
            print(f"{file_path}:{line_no}: {line}")
    else:
        print("No tags found.")