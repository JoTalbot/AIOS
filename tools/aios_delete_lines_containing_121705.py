# File: tools/todo_scanner.py

from pathlib import Path
from typing import Iterable, List, Tuple


def scan_for_tags(root_dir: str, tags: Iterable[str]) -> List[Tuple[str, int, str]]:
    """
    Walks the directory tree rooted at `root_dir`, reads all .py files,
    and returns a list of tuples (file_path, line_number, line_text) for
    each line that contains any of the specified `tags`.

    Parameters
    ----------
    root_dir : str
        Path to the root directory to scan.
    tags : Iterable[str]
        Iterable of tag strings to search for (case-sensitive).

    Returns
    -------
    List[Tuple[str, int, str]]
        List of occurrences. Each tuple contains the file path,
        the 1-based line number, and the line text.
    """
    occurrences: List[Tuple[str, int, str]] = []
    root = Path(root_dir)

    for py_file in root.rglob("*.py"):
        try:
            lines = py_file.read_text(encoding="utf-8").splitlines()
        except Exception:
            # Skip files that cannot be read
            continue

        for idx, line in enumerate(lines, start=1):
            if any(tag in line for tag in tags):
                occurrences.append((str(py_file), idx, line))

    return occurrences