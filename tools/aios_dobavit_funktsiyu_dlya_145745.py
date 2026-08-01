import re
import os
from dataclasses import dataclass
from typing import List, Dict

__all__ = ['scan_comments', 'get_technical_debt_report']

@dataclass
class Comment:
    """Dataclass to represent a comment."""
    line_number: int
    comment_type: str
    comment_text: str

def scan_comments(file_path: str) -> List[Comment]:
    """
    Scan a Python file for TODO/FIXME/HACK comments.

    Args:
    file_path (str): Path to the Python file.

    Returns:
    List[Comment]: List of comments found in the file.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            comments = []
            for i, line in enumerate(lines, start=1):
                match = re.search(r'(TODO|FIXME|HACK): (.*)', line)
                if match:
                    comments.append(Comment(i, match.group(1), match.group(2).strip()))
            return comments
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return []
    except Exception as e:
        print(f"Error scanning file {file_path}: {e}")
        return []

def get_technical_debt_report(file_paths: List[str]) -> Dict[str, int]:
    """
    Generate a technical debt report from a list of Python files.

    Args:
    file_paths (List[str]): List of paths to Python files.

    Returns:
    Dict[str, int]: Dictionary where keys are comment types and values are counts.
    """
    report = {}
    for file_path in file_paths:
        comments = scan_comments(file_path)
        for comment in comments:
            comment_type = comment.comment_type
            if comment_type in report:
                report[comment_type] += 1
            else:
                report[comment_type] = 1
    return report

def print_technical_debt_report(report: Dict[str, int]) -> None:
    """
    Print a technical debt report in a human-readable format.

    Args:
    report (Dict[str, int]): Dictionary where keys are comment types and values are counts.
    """
    print("Technical Debt Report:")
    for comment_type, count in report.items():
        print(f"{comment_type.capitalize()}: {count}")

if __name__ == '__main__':
    file_paths = ['path/to/file1.py', 'path/to/file2.py']
    report = get_technical_debt_report(file_paths)
    print_technical_debt_report(report)