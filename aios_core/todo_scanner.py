from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict

@dataclass
class TodoItem:
    """Dataclass to represent a TODO/FIXME/HACK item."""
    line_number: int
    text: str

class TodoScanner:
    """Class to scan Python files for TODO/FIXME/HACK items."""

    def __init__(self, path: Path):
        """Initialize the scanner with a target path."""
        self.path = path

    def scan(self) -> List[TodoItem]:
        """Scan the target path for TODO/FIXME/HACK items."""
        try:
            todo_items = []
            for file in self.path.rglob('*.py'):
                with open(file, 'r') as f:
                    for line_number, line in enumerate(f, start=1):
                        if any(keyword in line for keyword in ['TODO', 'FIXME', 'HACK']):
                            todo_items.append(TodoItem(line_number, line.strip()))
            return todo_items
        except FileNotFoundError:
            # Handle the case when the path does not exist
            return []

def test_todo_scanner():
    """Test the todo_scanner.scan() function."""
    scanner = TodoScanner(Path('./tests'))
    todo_items = scanner.scan()
    assert len(todo_items) == 3
    assert todo_items[0].line_number == 2
    assert todo_items[0].text == 'TODO: This is a TODO item.'
    assert todo_items[1].line_number == 5
    assert todo_items[1].text == 'FIXME: This is a FIXME item.'
    assert todo_items[2].line_number == 8
    assert todo_items[2].text == 'HACK: This is a HACK item.'

def test_todo_scanner_empty_path():
    """Test the todo_scanner.scan() function with an empty path."""
    scanner = TodoScanner(Path('./non_existent_path'))
    todo_items = scanner.scan()
    assert len(todo_items) == 0

def test_todo_scanner_no_todo_items():
    """Test the todo_scanner.scan() function with no TODO items."""
    scanner = TodoScanner(Path('./tests/no_todo_items'))
    todo_items = scanner.scan()
    assert len(todo_items) == 0

if __name__ == '__main__':
    test_todo_scanner()
    test_todo_scanner_empty_path()
    test_todo_scanner_no_todo_items()
    print('All tests passed.')