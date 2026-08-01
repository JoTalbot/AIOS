import os
import re
import dataclasses
from typing import List, Tuple

@dataclasses.dataclass
class ScanResult:
    """Result of scanning a file for TODO/FIXME/HACK comments."""
    file_path: str
    lines: List[Tuple[int, str]]

def scan_file_for_comments(file_path: str) -> ScanResult:
    """
    Scan a Python file for TODO/FIXME/HACK comments.

    Args:
    file_path: Path to the Python file to scan.

    Returns:
    ScanResult object containing the file path and a list of tuples, where each tuple contains the line number and the comment.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            result = []
            for i, line in enumerate(lines, start=1):
                match = re.search(r'^(?:TODO|FIXME|HACK):', line)
                if match:
                    result.append((i, line.strip()))
            return ScanResult(file_path, result)
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return ScanResult(file_path, [])
    except Exception as e:
        print(f"Error scanning file {file_path}: {e}")
        return ScanResult(file_path, [])

def scan_directory_for_comments(directory_path: str) -> List[ScanResult]:
    """
    Scan all Python files in a directory and its subdirectories for TODO/FIXME/HACK comments.

    Args:
    directory_path: Path to the directory to scan.

    Returns:
    List of ScanResult objects, one for each file scanned.
    """
    results = []
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                results.append(scan_file_for_comments(file_path))
    return results

def main():
    directory_path = 'tools'
    results = scan_directory_for_comments(directory_path)
    for result in results:
        print(f"File: {result.file_path}")
        for line in result.lines:
            print(f"  Line {line[0]}: {line[1]}")

if __name__ == '__main__':
    main()