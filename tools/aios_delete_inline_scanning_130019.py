# scan_todos.py
"""
Utility module to find TODO, FIXME, and HACK comments in a Python repository.

The :func:`find_todos_in_repo` function walks the given repository path,
searches all ``.py`` files for the specified keywords, and returns a list
of tuples containing the relative file path, line number, and the matched
comment text.

The module is designed to be imported by other tools and can also be run
directly from the command line for quick inspection.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

__all__ = ["find_todos_in_repo"]


def find_todos_in_repo(repo_path: str) -> List[Tuple[str, int, str]]:
    """
    Walk the repository located at *repo_path* and collect all TODO, FIXME,
    and HACK comments from Python files.

    Parameters
    ----------
    repo_path : str
        Path to the root of the repository to scan.

    Returns
    -------
    List[Tuple[str, int, str]]
        A list of tuples, each containing:
        - relative file path (str)
        - line number (int)
        - matched comment text (str)

    Raises
    ------
    ValueError
        If *repo_path* does not point to an existing directory.
    """
    todos: List[Tuple[str, int, str]] = []
    repo = Path(repo_path)

    if not repo.is_dir():
        raise ValueError(f"Repository path {repo_path!r} is not a directory")

    keyword_pattern = re.compile(r"\b(TODO|FIXME|HACK)\b(.*)")

    for py_file in repo.rglob("*.py"):
        try:
            with py_file.open("r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    match = keyword_pattern.search(line)
                    if match:
                        keyword = match.group(1)
                        comment = match.group(2).strip()
                        todos.append(
                            (
                                str(py_file.relative_to(repo)),
                                lineno,
                                f"{keyword}{comment}",
                            )
                        )
        except (OSError, UnicodeDecodeError) as exc:
            logging.warning(f"Could not read file {py_file}: {exc}")

    return todos


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) > 1:
        repo_dir = sys.argv[1]
    else:
        repo_dir = os.getcwd()

    try:
        found_todos = find_todos_in_repo(repo_dir)
    except Exception as exc:
        logging.error(f"Error scanning repository: {exc}")
        sys.exit(1)

    if not found_todos:
        print("No TODO/FIXME/HACK comments found.")
        sys.exit(0)

    for file_path, line_no, text in found_todos:
        print(f"{file_path}:{line_no} - {text}")