import os
import re
import unittest
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Tag:
    """Dataclass to represent a tag."""
    name: str
    line_number: int
    file_path: str

def find_tags(file_path: str) -> List[Tag]:
    """
    Find TODO/FIXME/HACK tags in a file.

    Args:
    file_path (str): Path to the file to search in.

    Returns:
    List[Tag]: List of tags found in the file.
    """
    try:
        with open(file_path, 'r') as file:
            content = file.readlines()
            tags = []
            for i, line in enumerate(content, start=1):
                match = re.search(r'(TODO|FIXME|HACK)', line)
                if match:
                    tags.append(Tag(match.group(1), i, file_path))
            return tags
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def find_tags_in_directory(directory_path: str) -> List[Tag]:
    """
    Find TODO/FIXME/HACK tags in all files in a directory.

    Args:
    directory_path (str): Path to the directory to search in.

    Returns:
    List[Tag]: List of tags found in the directory.
    """
    tags = []
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            tags.extend(find_tags(file_path))
    return tags

class TestTagFinder(unittest.TestCase):
    """Test class for tag finder functions."""

    def test_find_tags(self):
        """Test find_tags function."""
        tags = find_tags('tests/test_file.py')
        self.assertEqual(len(tags), 2)
        self.assertEqual(tags[0].name, 'TODO')
        self.assertEqual(tags[0].line_number, 1)
        self.assertEqual(tags[0].file_path, 'tests/test_file.py')
        self.assertEqual(tags[1].name, 'FIXME')
        self.assertEqual(tags[1].line_number, 2)
        self.assertEqual(tags[1].file_path, 'tests/test_file.py')

    def test_find_tags_in_directory(self):
        """Test find_tags_in_directory function."""
        tags = find_tags_in_directory('tests')
        self.assertGreater(len(tags), 0)

if __name__ == '__main__':
    unittest.main(argv=[os.path.basename(__file__)])
    __all__ = ['find_tags', 'find_tags_in_directory']