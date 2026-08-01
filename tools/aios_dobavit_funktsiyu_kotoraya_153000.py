from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict
import re

@dataclass
class TodoItem:
    """Dataclass to represent a TODO/FIXME/HACK item."""
    path: str
    text: str

class TodoScanner:
    """Class to scan files for TODO/FIXME/HACK comments."""

    def __init__(self, target_path: Path):
        """Initialize the scanner with the target path."""
        self.target_path = target_path

    def scan_files(self) -> List[TodoItem]:
        """Scan all files in the target path for TODO/FIXME/HACK comments."""
        try:
            todo_items = []
            for file_path in self.target_path.rglob('*'):
                if file_path.is_file():
                    with open(file_path, 'r') as file:
                        content = file.read()
                        matches = re.findall(r'(TODO|FIXME|HACK): (.*)', content)
                        for match in matches:
                            todo_items.append(TodoItem(str(file_path), match[1]))
            return todo_items
        except Exception as e:
            print(f"Error scanning files: {e}")
            return []

def save_results(todo_items: List[TodoItem], output_path: Path):
    """Save the TODO/FIXME/HACK items to a file."""
    try:
        with open(output_path, 'w') as file:
            for item in todo_items:
                file.write(f"{item.path}: {item.text}\n")
    except Exception as e:
        print(f"Error saving results: {e}")

def main():
    """Main function to test the TodoScanner."""
    target_path = Path('tools')
    scanner = TodoScanner(target_path)
    todo_items = scanner.scan_files()
    save_results(todo_items, Path('todo_results.txt'))

if __name__ == '__main__':
    main()
    __all__ = ['TodoItem', 'TodoScanner', 'save_results']