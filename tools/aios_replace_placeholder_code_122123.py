# tools/aios_replace_placeholder_code_122123.py
"""
Utility module to scan Python files for common TODO-like tags.

The :func:`scan_todos` function recursively walks a directory tree,
searches for the tags ``TODO``, ``FIXME``, ``HACK``, ``XXX`` and ``BUG``,
and returns a list of dictionaries containing the file path, line number,
tag, and the full line where the tag was found.  A summary of the counts
per tag is printed to the console.

The module can be executed directly to perform a scan on the current
working directory.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Union

__all__ = ["scan_todos"]


def _iter_python_files(root: Path) -> Iterable[Path]:
    """
    Yield all ``.py`` files under *root* recursively.

    Parameters
    ----------
    root : Path
        Root directory to start the search.

    Yields
    ------
    Path
        Path to a Python file.
    """
    for file_path in root.rglob("*.py"):
        if file_path.is_file():
            yield file_path


def scan_todos(root: Union[str, Path] = Path.cwd()) -> List[Dict[str, Any]]:
    """
    Recursively scan *root* for Python files containing TODO-like tags.

    Parameters
    ----------
    root : Union[str, Path], optional
        Directory to start scanning from. Defaults to the current working
        directory.

    Returns
    -------
    List[Dict[str, Any]]
        A list of dictionaries, each containing:
        - ``file``: Path to the file (string)
        - ``line_number``: Line number where the tag was found (int)
        - ``tag``: The matched tag (str)
        - ``line``: The full line of text (str)

    The function also prints a summary of the total counts per tag.
    """
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ValueError(f"Provided root path '{root}' is not a directory.")

    tags = ["TODO", "FIXME", "HACK", "XXX", "BUG"]
    tag_pattern = re.compile(r"\b(" + "|".join(tags) + r")\b")

    results: List[Dict[str, Any]] = []

    for file_path in _iter_python_files(root_path):
        try:
            with file_path.open(encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    match = tag_pattern.search(line)
                    if match:
                        results.append(
                            {
                                "file": str(file_path),
                                "line_number": line_no,
                                "tag": match.group(0),
                                "line": line.rstrip("\n"),
                            }
                        )
        except (OSError, UnicodeDecodeError) as exc:
            # Skip files that cannot be read or decoded
            print(f"Warning: Skipping file '{file_path}': {exc}")

    # Summary
    counter = Counter(item["tag"] for item in results)
    if counter:
        summary_lines = [f"Found {count} {tag}(s)" for tag, count in counter.items()]
        print("\n".join(summary_lines))
    else:
        print("No TODO-like tags found.")

    return results


if __name__ == "__main__":
    # When executed as a script, scan the current working directory.
    scan_todos()