import re
import unittest
from dataclasses import dataclass
from typing import List, Optional

__all__ = ['find_comments', 'CommentFinder']

@dataclass
class Comment:
    """Dataclass to hold comment information."""
    line_number: int
    comment_type: str
    comment_text: str

class CommentFinder:
    """Class to find comments in code."""

    def __init__(self, code: str):
        """Initialize the CommentFinder with code."""
        self.code = code

    def find_comments(self) -> List[Comment]:
        """Find comments in the code."""
        comments = []
        for line_number, line in enumerate(self.code.split('\n'), start=1):
            match = re.search(r'^(TODO|FIXME|HACK|OPTIMIZE|NOTE):', line, re.IGNORECASE)
            if match:
                comments.append(Comment(line_number, match.group(1).upper(), line.strip()))
        return comments

def find_comments(code: str) -> List[Comment]:
    """Find comments in the code."""
    return CommentFinder(code).find_comments()

class TestCommentFinder(unittest.TestCase):
    """Test class for CommentFinder."""

    def test_find_comments(self):
        """Test finding comments."""
        code = """
        # TODO: This is a TODO comment
        # FIXME: This is a FIXME comment
        # HACK: This is a HACK comment
        # OPTIMIZE: This is an OPTIMIZE comment
        # NOTE: This is a NOTE comment
        """
        comments = find_comments(code)
        self.assertEqual(len(comments), 5)
        self.assertEqual(comments[0].comment_type, 'TODO')
        self.assertEqual(comments[1].comment_type, 'FIXME')
        self.assertEqual(comments[2].comment_type, 'HACK')
        self.assertEqual(comments[3].comment_type, 'OPTIMIZE')
        self.assertEqual(comments[4].comment_type, 'NOTE')

    def test_find_comments_no_comments(self):
        """Test finding comments with no comments."""
        code = """
        # This is a normal comment
        """
        comments = find_comments(code)
        self.assertEqual(len(comments), 0)

    def test_find_comments_no_code(self):
        """Test finding comments with no code."""
        comments = find_comments('')
        self.assertEqual(len(comments), 0)

if __name__ == '__main__':
    unittest.main()