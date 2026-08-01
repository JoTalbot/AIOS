# tools/aios_dobavit_testy_dlya_154226.py

from dataclasses import dataclass
from pathlib import Path
import re
import unittest

__all__ = ['scan_for_todo_fixme_hack', 'run_tests']

@dataclass
class TodoFixmeHack:
    """Class to represent a TODO or FIXME hack."""
    path: Path
    line_number: int
    message: str

def scan_for_todo_fixme_hack(path: Path) -> list[TodoFixmeHack]:
    """
    Scan the given path for TODO and FIXME comments.

    Args:
    path: Path to scan for TODO and FIXME comments.

    Returns:
    List of TodoFixmeHack objects containing the path, line number, and message.
    """
    hacks = []
    with open(path, 'r') as file:
        for line_number, line in enumerate(file, start=1):
            if re.search(r'# TODO|FIXME', line):
                match = re.search(r'# (TODO|FIXME): (.*)', line)
                if match:
                    hacks.append(TodoFixmeHack(path, line_number, match.group(2)))
    return hacks

class TestTodoFixmeHack(unittest.TestCase):
    def test_scan_for_todo_fixme_hack(self):
        # Arrange
        path = Path('path/to/file.py')
        expected_hacks = [
            TodoFixmeHack(path, 10, 'Hack 1'),
            TodoFixmeHack(path, 20, 'Hack 2')
        ]
        with open(path, 'w') as file:
            file.write('# TODO: Hack 1\n')
            file.write('# FIXME: Hack 2\n')

        # Act
        hacks = scan_for_todo_fixme_hack(path)

        # Assert
        self.assertEqual(hacks, expected_hacks)

    def test_scan_for_todo_fixme_hack_empty_file(self):
        # Arrange
        path = Path('path/to/file.py')
        expected_hacks = []

        # Act
        hacks = scan_for_todo_fixme_hack(path)

        # Assert
        self.assertEqual(hacks, expected_hacks)

    def test_scan_for_todo_fixme_hack_no_todo_fixme(self):
        # Arrange
        path = Path('path/to/file.py')
        expected_hacks = []
        with open(path, 'w') as file:
            file.write('print("Hello World")\n')

        # Act
        hacks = scan_for_todo_fixme_hack(path)

        # Assert
        self.assertEqual(hacks, expected_hacks)

def run_tests():
    """Run the tests."""
    unittest.main(argv=[__file__])

if __name__ == '__main__':
    run_tests()