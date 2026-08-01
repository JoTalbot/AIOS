import os
import re
import unittest
from dataclasses import dataclass
from typing import List

@dataclass
class Comment:
    """Dataclass to represent a comment."""
    line: int
    text: str

def find_comments(file_path: str) -> List[Comment]:
    """
    Find TODO/FIXME/HACK comments in a file.

    Args:
    file_path (str): Path to the file to search.

    Returns:
    List[Comment]: List of comments found in the file.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            comments = []
            for i, line in enumerate(lines, start=1):
                if re.search(r'\b(TODO|FIXME|HACK)\b', line, re.IGNORECASE):
                    comments.append(Comment(i, line.strip()))
            return comments
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def test_find_comments():
    """
    Test the find_comments function.
    """
    test_dir = os.path.dirname(__file__)
    file_path = os.path.join(test_dir, 'test_file.txt')
    with open(file_path, 'w') as file:
        file.write("# TODO: This is a TODO comment.\n")
        file.write("# FIXME: This is a FIXME comment.\n")
        file.write("# HACK: This is a HACK comment.\n")
    comments = find_comments(file_path)
    assert len(comments) == 3
    for comment in comments:
        assert comment.text.startswith('# ')
        assert comment.text.endswith('comment.')
    os.remove(file_path)

class TestFindComments(unittest.TestCase):
    """
    Test case for the find_comments function.
    """
    def test_find_comments(self):
        test_find_comments()

if __name__ == '__main__':
    unittest.main(argv=[os.path.basename(__file__)])