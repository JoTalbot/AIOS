# code_scan.py
"""
Utility module for scanning source files for common development markers.

The module provides two public functions:

* :func:`scan_file_for_markers` – scans a single file for the markers
  ``TODO``, ``FIXME``, ``HACK``, ``XXX`` and ``BUG``.
* :func:`scan_directory` – walks a directory tree, applies
  :func:`scan_file_for_markers` to every file that matches a list of
  extensions and aggregates the results.

Both functions return a list of dictionaries with the keys ``tag``,
``line_number`` and ``line_text``.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

__all__ = ["scan_file_for_markers", "scan_directory"]


@dataclass(frozen=True)
class Marker:
    """Represents a single marker found in a source file."""
    tag: str
    line_number: int
    line_text: str

    def to_dict(self) -> Dict[str, Any]:
        """Return a serialisable representation of the marker."""
        return {
            "tag": self.tag,
            "line_number": self.line_number,
            "line_text": self.line_text,
        }


# Pre‑compiled regular expression that matches any of the markers.
_MARKER_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX|BUG)\b", re.IGNORECASE)


def scan_file_for_markers(file_path: str) -> List[Dict[str, Any]]:
    """
    Scan a single file for development markers.

    Parameters
    ----------
    file_path : str
        Path to the file to be scanned.

    Returns
    -------
    List[Dict[str, Any]]
        A list of dictionaries, each containing the keys ``tag``,
        ``line_number`` and ``line_text`` for a found marker.

    Notes
    -----
    The function is tolerant to I/O errors; if a file cannot be read,
    an empty list is returned and the error is logged to ``stderr``.
    """
    markers: List[Marker] = []

    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            for idx, line in enumerate(fh, start=1):
                if _MARKER_RE.search(line):
                    # Extract the first matching tag for clarity.
                    tag = _MARKER_RE.search(line).group(1).upper()
                    markers.append(Marker(tag, idx, line.rstrip("\n")))
    except (OSError, UnicodeDecodeError) as exc:
        # Gracefully handle unreadable files.
        print(f"Warning: Could not read {file_path!r}: {exc}", file=sys.stderr)

    return [m.to_dict() for m in markers]


def _is_valid_extension(file_name: str, extensions: Sequence[str]) -> bool:
    """Check if the file has one of the desired extensions."""
    return any(file_name.lower().endswith(ext.lower()) for ext in extensions)


def scan_directory(dir_path: str, extensions: List[str]) -> List[Dict[str, Any]]:
    """
    Walk a directory tree and aggregate markers from all matching files.

    Parameters
    ----------
    dir_path : str
        Root directory to start scanning from.
    extensions : List[str]
        List of file extensions to include (e.g. ``['.py', '.js']``).

    Returns
    -------
    List[Dict[str, Any]]
        Aggregated list of marker dictionaries from all scanned files.
    """
    aggregated: List[Dict[str, Any]] = []

    for root, _, files in os.walk(dir_path):
        for file_name in files:
            if _is_valid_extension(file_name, extensions):
                full_path = os.path.join(root, file_name)
                aggregated.extend(scan_file_for_markers(full_path))

    return aggregated


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print(
            "Usage: python code_scan.py <directory> <ext1> [<ext2> ...]",
            file=sys.stderr,
        )
        sys.exit(1)

    root_dir = sys.argv[1]
    exts = sys.argv[2:]

    results = scan_directory(root_dir, exts)
    print(json.dumps(results, indent=2))