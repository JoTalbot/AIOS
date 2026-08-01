# tools/aios_dobavit_yunit_testy_155337.py

import os
import re
from dataclasses import dataclass
from typing import List, Optional
import unittest

__all__ = ['find_todo_fixme_hack', 'TodoFixmeHackFinder']

@dataclass
class TodoFixmeHackFinder:
    """Class to find TODO/FIXME/HACK comments in files."""
    target_comments: List[str] = ['TODO', 'FIXME', 'HACK']

    def find(self, path: str) -> List[str]:
        """Find TODO/FIXME/HACK comments in files.

        Args:
            path: Path to the directory to scan.

        Returns:
            List of files with TODO/FIXME/HACK comments.
        """
        files_with_comments = []
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        for comment in self.target_comments:
                            if re.search(r'\b' + comment + r'\b', content, re.IGNORECASE):
                                files_with_comments.append(file_path)
                                break
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")
        return files_with_comments


def find_todo_fixme_hack(path: str) -> List[str]:
    """Find TODO/FIXME/HACK comments in files.

    Args:
        path: Path to the directory to scan.

    Returns:
        List of files with TODO/FIXME/HACK comments.
    """
    finder = TodoFixmeHackFinder()
    return finder.find(path)


class TestTodoFixmeHackFinder(unittest.TestCase):
    def test_find_todo_fixme_hack(self):
        finder = TodoFixmeHackFinder()
        files_with_comments = finder.find('./tests')
        self.assertGreater(len(files_with_comments), 0)

    def test_find_no_todo_fixme_hack(self):
        finder = TodoFixmeHackFinder()
        files_with_comments = finder.find('./tests/no_comments')
        self.assertEqual(files_with_comments, [])

    def test_find_empty_directory(self):
        finder = TodoFixmeHackFinder()
        files_with_comments = finder.find('./tests/empty_directory')
        self.assertEqual(files_with_comments, [])

if __name__ == '__main__':
    unittest.main()