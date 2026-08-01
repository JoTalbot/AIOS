import os
import re
from dataclasses import dataclass
from typing import List

@dataclass
class Comment:
    """Dataclass to represent a comment."""
    line: int
    text: str

def find_comments_in_file(file_path: str) -> List[Comment]:
    """
    Find TODO/FIXME/HACK comments in a Python file.

    Args:
    file_path (str): Path to the Python file.

    Returns:
    List[Comment]: List of comments found in the file.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            comments = []
            for i, line in enumerate(lines, 1):
                match = re.search(r'#\s*(TODO|FIXME|HACK)', line)
                if match:
                    comments.append(Comment(i, match.group(0).strip()))
            return comments
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return []
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return []

def find_comments_in_project(project_path: str) -> List[Comment]:
    """
    Find TODO/FIXME/HACK comments in all Python files in a project.

    Args:
    project_path (str): Path to the project.

    Returns:
    List[Comment]: List of comments found in the project.
    """
    comments = []
    for root, dirs, files in os.walk(project_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                comments.extend(find_comments_in_file(file_path))
    return comments

def generate_report(comments: List[Comment]) -> str:
    """
    Generate a report from the comments.

    Args:
    comments (List[Comment]): List of comments.

    Returns:
    str: Report as a string.
    """
    report = "Technical Debt Report:\n"
    for comment in comments:
        report += f"Line {comment.line}: {comment.text}\n"
    return report

def main():
    project_path = 'tools'
    comments = find_comments_in_project(project_path)
    report = generate_report(comments)
    print(report)

if __name__ == '__main__':
    main()