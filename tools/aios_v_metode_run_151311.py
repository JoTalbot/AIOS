import os
import re
from dataclasses import dataclass
from typing import List

@dataclass
class Todo:
    """Data class to represent a TODO/FIXME/HACK tag."""
    file_path: str
    line_number: int
    tag: str
    description: str

def scan_todos(target_path: str) -> List[Todo]:
    """
    Scan Python files for TODO/FIXME/HACK tags and return a list of Todo objects.

    Args:
    target_path (str): The path to the directory containing Python files to scan.

    Returns:
    List[Todo]: A list of Todo objects containing the file path, line number, tag, and description.
    """
    todos = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r") as f:
                    for line_number, line in enumerate(f, start=1):
                        match = re.search(r"^(?:TODO|FIXME|HACK):?\s*(.*)", line)
                        if match:
                            tag = match.group(1).strip()
                            todos.append(Todo(file_path, line_number, match.group(0).split(":")[0].strip(), tag))
    return todos

def main():
    """Test the scan_todos function."""
    target_path = "tools"
    todos = scan_todos(target_path)
    for todo in todos:
        print(f"File: {todo.file_path}, Line: {todo.line_number}, Tag: {todo.tag}, Description: {todo.description}")

if __name__ == "__main__":
    main()
    __all__ = ["scan_todos"]