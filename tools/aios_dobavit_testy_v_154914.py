# tools/aios_dobavit_testy_v_154914.py

"""
Module for testing TODO, FIXME, and HACK comments in Python files.
"""

import os
import re
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Comment:
    """Dataclass for storing comment information."""
    line_number: int
    comment_type: str
    comment_text: str

def scan_comments(file_path: str) -> List[Comment]:
    """
    Scan a Python file for TODO, FIXME, and HACK comments.

    Args:
    file_path (str): Path to the Python file to scan.

    Returns:
    List[Comment]: List of comments found in the file.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            comments = []
            for i, line in enumerate(lines, start=1):
                match = re.search(r'^(?:#|//|"""|\'\'\')\s*(TODO|FIXME|HACK)\s*(.*)', line)
                if match:
                    comments.append(Comment(i, match.group(1), match.group(2).strip()))
            return comments
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return []
    except Exception as e:
        print(f"Error scanning file {file_path}: {e}")
        return []

def test_scan_comments(tmp_path):
    """
    Test function for scan_comments.
    """
    file_path = tmp_path / "test_file.py"
    with open(file_path, 'w') as file:
        file.write("# TODO: This is a TODO comment\n")
        file.write("# FIXME: This is a FIXME comment\n")
        file.write("# HACK: This is a HACK comment\n")

    comments = scan_comments(str(file_path))
    assert len(comments) == 3
    assert comments[0].comment_type == "TODO"
    assert comments[1].comment_type == "FIXME"
    assert comments[2].comment_type == "HACK"

def test_scan_comments_no_comments(tmp_path):
    """
    Test function for scan_comments.
    """
    file_path = tmp_path / "test_file.py"
    with open(file_path, 'w') as file:
        file.write("This is a regular line of code.")

    comments = scan_comments(str(file_path))
    assert len(comments) == 0

def test_scan_comments_invalid_file(tmp_path):
    """
    Test function for scan_comments.
    """
    file_path = tmp_path / "test_file.py"
    with open(file_path, 'w') as file:
        file.write("This is a regular line of code.")

    # Try to scan a non-Python file
    comments = scan_comments(str(file_path) + ".txt")
    assert len(comments) == 0

def test_scan_comments_invalid_path():
    """
    Test function for scan_comments.
    """
    comments = scan_comments("non_existent_file.py")
    assert len(comments) == 0

if __name__ == '__main__':
    import pytest
    pytest.main([__file__, "-v"])