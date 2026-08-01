"""
Module for removing all TODO/FIXME comments from a specified range of lines in a file.
"""

import os
import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class FileModificationResult:
    """Result of file modification."""
    modified: bool
    message: Optional[str]

def remove_todo_fixme(file_path: str, start_line: int, end_line: int) -> FileModificationResult:
    """
    Remove all TODO/FIXME comments from a specified range of lines in a file.

    Args:
    - file_path: Path to the file to modify.
    - start_line: First line number to remove TODO/FIXME comments from (inclusive).
    - end_line: Last line number to remove TODO/FIXME comments from (inclusive).

    Returns:
    - FileModificationResult: Result of file modification.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()

        modified = False
        message = ""

        for i, line in enumerate(lines, start=1):
            if start_line <= i <= end_line:
                if re.search(r'# TODO|# FIXME', line):
                    lines[i-1] = re.sub(r'# TODO|# FIXME', '', line).strip()
                    modified = True
                    message += f"Removed TODO/FIXME comment from line {i}.\n"

        if modified:
            with open(file_path, 'w') as file:
                file.writelines(lines)

        return FileModificationResult(modified, message)
    except FileNotFoundError:
        return FileModificationResult(False, f"File '{file_path}' not found.")
    except Exception as e:
        return FileModificationResult(False, f"An error occurred: {str(e)}")

def main():
    """
    Test the remove_todo_fixme function.
    """
    file_path = "path_to_your_file.py"
    start_line = 147
    end_line = 158

    result = remove_todo_fixme(file_path, start_line, end_line)

    if result.modified:
        print(result.message)
    else:
        print(result.message)

if __name__ == '__main__':
    main()

__all__ = ['remove_todo_fixme']