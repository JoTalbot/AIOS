from dataclasses import dataclass
from pathlib import Path
import re

__all__ = ['find_todos']

@dataclass
class Todo:
    """Dataclass to represent a TODO/FIXME/HACK comment."""
    line_number: int
    comment: str
    file_path: str

def find_todos(target_path: Path) -> list[Todo]:
    """
    Scan all files in the target path and its subdirectories for TODO/FIXME/HACK comments.

    Args:
    target_path: Path to the target directory.

    Returns:
    List of Todo objects containing the TODO/FIXME/HACK comments.
    """
    todos = []
    for file_path in target_path.rglob('*.py'):
        try:
            with file_path.open('r') as file:
                for line_number, line in enumerate(file, start=1):
                    match = re.search(r'(?m)^#?\s*(TODO|FIXME|HACK)', line)
                    if match:
                        todos.append(Todo(line_number, match.group(), str(file_path)))
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    return todos

def add_todos_to_list(todos: list[Todo], todos_list: list[Todo]) -> None:
    """
    Add the found TODO/FIXME/HACK comments to the given list.

    Args:
    todos: List of Todo objects to add.
    todos_list: List to add the Todo objects to.
    """
    todos_list.extend(todos)

def run_coder_orchestrator(target_path: Path) -> None:
    """
    Run the coder orchestrator with the given target path.

    Args:
    target_path: Path to the target directory.
    """
    todos = find_todos(target_path)
    # Add the found TODO/FIXME/HACK comments to the list
    add_todos_to_list(todos, todos)

if __name__ == '__main__':
    target_path = Path('tools/aios_vnesti_izmeneniya_v_170313.py')
    run_coder_orchestrator(target_path)
    print("Found TODO/FIXME/HACK comments:")
    for todo in find_todos(target_path):
        print(f"{todo.file_path}:{todo.line_number} - {todo.comment}")