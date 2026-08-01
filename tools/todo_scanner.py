import json
import os
import re
from dataclasses import dataclass
from typing import List

__all__ = ['TodoScanner', 'find_tags']

@dataclass
class TodoItem:
    """Represents a todo item with its tags."""
    text: str
    tags: List[str]

class TodoScanner:
    """Scans a directory for todo items and extracts their tags."""

    def __init__(self, path: str):
        """Initializes the TodoScanner instance.

        Args:
            path (str): The path to the directory to scan.
        """
        self.path = path

    def _find_todo_items(self) -> List[TodoItem]:
        """Finds todo items in the directory and extracts their tags.

        Returns:
            List[TodoItem]: A list of todo items with their tags.
        """
        todo_items = []
        for root, dirs, files in os.walk(self.path):
            for file in files:
                if file.endswith(('.txt', '.md', '.markdown')):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                        tags = self._extract_tags(text)
                        todo_items.append(TodoItem(text, tags))
        return todo_items

    def _extract_tags(self, text: str) -> List[str]:
        """Extracts tags from the given text.

        Args:
            text (str): The text to extract tags from.

        Returns:
            List[str]: A list of extracted tags.
        """
        pattern = r'\[(.*?)\]'
        return re.findall(pattern, text)

    def find_tags(self) -> str:
        """Finds todo items in the directory and returns their tags in JSON format.

        Returns:
            str: A JSON string containing the tags of the found todo items.
        """
        try:
            todo_items = self._find_todo_items()
            tags = [item.tags for item in todo_items]
            return json.dumps(tags)
        except Exception as e:
            print(f"Error: {e}")
            return json.dumps([])

def main():
    """Runs the TodoScanner instance and prints the found tags."""
    scanner = TodoScanner('path_to_your_directory')
    print(scanner.find_tags())

if __name__ == '__main__':
    main()