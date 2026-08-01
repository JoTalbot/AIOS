import json
import os
import re
from dataclasses import dataclass
from typing import List, Dict
import unittest

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
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            text = f.read()
                            tags = self._extract_tags(text)
                            todo_items.append(TodoItem(text, tags))
                    except Exception as e:
                        print(f"Error reading file {file_path}: {e}")
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

    def find_todo_comments(self) -> List[str]:
        """Finds TODO/FIXME/HACK comments in the directory.

        Returns:
            List[str]: A list of found TODO/FIXME/HACK comments.
        """
        comments = []
        for root, dirs, files in os.walk(self.path):
            for file in files:
                if file.endswith(('.txt', '.md', '.markdown')):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            text = f.read()
                            comments.extend(self._extract_comments(text))
                    except Exception as e:
                        print(f"Error reading file {file_path}: {e}")
        return comments

    def _extract_comments(self, text: str) -> List[str]:
        """Extracts TODO/FIXME/HACK comments from the given text.

        Args:
            text (str): The text to extract comments from.

        Returns:
            List[str]: A list of extracted comments.
        """
        pattern = r'(TODO|FIXME|HACK).*'
        return re.findall(pattern, text, re.IGNORECASE)

def find_tags(path: str) -> str:
    """Finds todo items in the given directory and returns their tags in JSON format.

    Args:
        path (str): The path to the directory to scan.

    Returns:
        str: A JSON string containing the tags of the found todo items.
    """
    scanner = TodoScanner(path)
    return scanner.find_tags()

def find_todo_comments(path: str) -> List[str]:
    """Finds TODO/FIXME/HACK comments in the given directory.

    Args:
        path (str): The path to the directory to scan.

    Returns:
        List[str]: A list of found TODO/FIXME/HACK comments.
    """
    scanner = TodoScanner(path)
    return scanner.find_todo_comments()

class TestTodoScanner(unittest.TestCase):
    """Tests the TodoScanner class."""

    def test_find_tags(self):
        """Tests the find_tags method."""
        path = 'path_to_your_directory'
        tags = find_tags(path)
        self.assertIsInstance(tags, str)
        self.assertTrue(tags.startswith('[') and tags.endswith(']'))

    def test_find_tags_empty_directory(self):
        """Tests the find_tags method with an empty directory."""
        path = 'empty_directory'
        tags = find_tags(path)
        self.assertIsInstance(tags, str)
        self.assertEqual(tags, '[]')

    def test_find_tags_invalid_path(self):
        """Tests the find_tags method with an invalid path."""
        path = 'invalid_path'
        tags = find_tags(path)
        self.assertIsInstance(tags, str)
        self.assertEqual(tags, '[]')

    def test_find_todo_comments(self):
        """Tests the find_todo_comments method."""
        path = 'path_to_your_directory'
        comments = find_todo_comments(path)
        self.assertIsInstance(comments, list)

    def test_find_todo_comments_empty_directory(self):
        """Tests the find_todo_comments method with an empty directory."""
        path = 'empty_directory'
        comments = find_todo_comments(path)
        self.assertIsInstance(comments, list)
        self.assertEqual(comments, [])

    def test_find_todo_comments_invalid_path(self):
        """Tests the find_todo_comments method with an invalid path."""
        path = 'invalid_path'
        comments = find_todo_comments(path)
        self.assertIsInstance(comments, list)
        self.assertEqual(comments, [])

if __name__ == '__main__':
    unittest.main(argv=[os.path.basename(__file__)])