import os
import re
from dataclasses import dataclass
from typing import List

@dataclass
class TodoItem:
    """Dataclass to represent a TODO item."""
    file_path: str
    line_number: int
    item_type: str
    item_text: str

def scan_repository_for_todos(target_path: str) -> List[TodoItem]:
    """
    Scan the repository for TODO/FIXME/HACK comments.

    Args:
    target_path: The path to the repository root.

    Returns:
    A list of TodoItem objects containing the file path, line number, item type, and item text.
    """
    todos = []
    for root, _, files in os.walk(target_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r") as f:
                        for line_number, line in enumerate(f, start=1):
                            match = re.search(r"(TODO|FIXME|HACK): (.*)", line)
                            if match:
                                todos.append(TodoItem(
                                    file_path=file_path,
                                    line_number=line_number,
                                    item_type=match.group(1),
                                    item_text=match.group(2).strip()
                                ))
                except Exception as e:
                    print(f"Error scanning file {file_path}: {e}")
    return todos

def print_todos(todos: List[TodoItem]) -> None:
    """
    Print the list of TODO items to the console.

    Args:
    todos: A list of TodoItem objects.
    """
    for todo in todos:
        print(f"{todo.file_path}:{todo.line_number} - {todo.item_type}: {todo.item_text}")

def main() -> None:
    """
    The main entry point of the script.
    """
    target_path = "tools/aios_dobavit_funktsiyu_skanirovaniya_153044.py"
    todos = scan_repository_for_todos(os.path.dirname(target_path))
    print_todos(todos)

if __name__ == "__main__":
    main()