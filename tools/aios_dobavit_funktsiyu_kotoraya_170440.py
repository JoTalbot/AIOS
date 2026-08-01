import json
import os
import re
from dataclasses import dataclass
from typing import List

@dataclass
class TodoItem:
    """Represents a TODO/FIXME/HACK comment."""
    path: str
    line_number: int
    comment: str

def scan_project_for_todo_comments(target_path: str) -> List[TodoItem]:
    """
    Scans the project for TODO/FIXME/HACK comments and returns a list of TodoItem objects.

    Args:
    target_path: The path to the project root.

    Returns:
    A list of TodoItem objects containing the path, line number, and comment for each TODO/FIXME/HACK comment found.
    """
    todo_comments = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r") as f:
                    for line_number, line in enumerate(f, 1):
                        match = re.search(r"(TODO|FIXME|HACK): (.*)", line)
                        if match:
                            comment = match.group(2).strip()
                            todo_comments.append(TodoItem(file_path, line_number, comment))
    return todo_comments

def generate_json_report(todo_items: List[TodoItem]) -> str:
    """
    Generates a JSON report from the list of TODO/FIXME/HACK comments.

    Args:
    todo_items: A list of TodoItem objects.

    Returns:
    A JSON string representing the report.
    """
    report = {"todo_comments": []}
    for item in todo_items:
        report["todo_comments"].append({
            "path": item.path,
            "line_number": item.line_number,
            "comment": item.comment
        })
    return json.dumps(report, indent=4)

def main():
    target_path = "tools"
    todo_items = scan_project_for_todo_comments(target_path)
    report = generate_json_report(todo_items)
    print(report)

if __name__ == "__main__":
    main()