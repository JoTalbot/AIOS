"""
Module for removing TODO/FIXME/HACK comments from a given text.

Target path: tools/aios_udalit_kommentarii_todofixmehack_155925.py
"""

import re
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Comment:
    """Dataclass for representing a comment."""
    text: str
    type: str

def remove_comments(text: str) -> str:
    """
    Remove TODO/FIXME/HACK comments from a given text.

    Args:
    text (str): The text to remove comments from.

    Returns:
    str: The text with comments removed.
    """
    # Regular expression pattern for matching TODO/FIXME/HACK comments
    pattern = r'#\s*(TODO|FIXME|HACK):\s*(.*)'
    # Use re.sub to replace all occurrences of the pattern with an empty string
    return re.sub(pattern, '', text, flags=re.MULTILINE)

def find_comments(text: str) -> List[Comment]:
    """
    Find all TODO/FIXME/HACK comments in a given text.

    Args:
    text (str): The text to find comments in.

    Returns:
    List[Comment]: A list of comments found in the text.
    """
    # Regular expression pattern for matching TODO/FIXME/HACK comments
    pattern = r'#\s*(TODO|FIXME|HACK):\s*(.*)'
    # Use re.findall to find all occurrences of the pattern
    comments = re.findall(pattern, text, flags=re.MULTILINE)
    # Convert the list of tuples to a list of Comment objects
    return [Comment(comment[1], comment[0]) for comment in comments]

def main():
    """
    Test the remove_comments and find_comments functions.
    """
    text = """
# TODO: This is a TODO comment
# FIXME: This is a FIXME comment
# HACK: This is a HACK comment
"""
    print("Original text:")
    print(text)
    print("\nText with comments removed:")
    print(remove_comments(text))
    print("\nComments found:")
    for comment in find_comments(text):
        print(f"{comment.type}: {comment.text}")

if __name__ == '__main__':
    main()
__all__ = ['remove_comments', 'find_comments']