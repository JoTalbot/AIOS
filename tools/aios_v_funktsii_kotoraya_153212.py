"""
Module for scanning Python files in a repository for TODO/FIXME/HACK comments.

Usage:
    - Run this script in the root directory of your repository.
    - It will scan all Python files and print out the results.
"""

import ast
import os
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Comment:
    """Dataclass for storing a comment."""
    line: int
    text: str

@dataclass
class FileResult:
    """Dataclass for storing the result of a file scan."""
    file_path: str
    comments: List[Comment]

def scan_file(file_path: str) -> FileResult:
    """
    Scan a single file for TODO/FIXME/HACK comments.

    Args:
        file_path: Path to the file to scan.

    Returns:
        A FileResult object containing the results of the scan.
    """
    try:
        with open(file_path, 'r') as file:
            tree = ast.parse(file.read())
            comments = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
                    comment = Comment(node.lineno, node.value.s)
                    comments.append(comment)
            return FileResult(file_path, comments)
    except Exception as e:
        print(f"Error scanning file {file_path}: {e}")
        return FileResult(file_path, [])

def scan_repository(target_path: str) -> List[FileResult]:
    """
    Scan all Python files in the repository for TODO/FIXME/HACK comments.

    Args:
        target_path: Path to the root directory of the repository.

    Returns:
        A list of FileResult objects containing the results of the scan.
    """
    results = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                results.append(scan_file(file_path))
    return results

def print_results(results: List[FileResult]) -> None:
    """
    Print out the results of the scan.

    Args:
        results: A list of FileResult objects containing the results of the scan.
    """
    for result in results:
        print(f"File: {result.file_path}")
        for comment in result.comments:
            print(f"  - Line {comment.line}: {comment.text}")
        print()

if __name__ == '__main__':
    target_path = os.path.dirname(__file__)
    results = scan_repository(target_path)
    print_results(results)

__all__ = ['scan_file', 'scan_repository', 'print_results']