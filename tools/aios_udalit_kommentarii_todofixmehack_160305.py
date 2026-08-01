import re
from dataclasses import dataclass
from typing import List

@dataclass
class Comment:
    """Class to represent a comment."""
    line_number: int
    comment_type: str
    comment_text: str

def extract_comments(file_path: str) -> List[Comment]:
    """
    Extracts TODO, FIXME, and HACK comments from a file.

    Args:
    file_path (str): Path to the file to extract comments from.

    Returns:
    List[Comment]: List of extracted comments.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            comments = []
            for i, line in enumerate(lines, start=1):
                match = re.search(r'#\s*(TODO|FIXME|HACK):', line)
                if match:
                    comment_type = match.group(1)
                    comment_text = line.strip().split(': ', 1)[1].strip()
                    comments.append(Comment(i, comment_type, comment_text))
            return comments
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def replace_comments(file_path: str, comments: List[Comment]) -> None:
    """
    Replaces TODO, FIXME, and HACK comments with their corresponding documentation.

    Args:
    file_path (str): Path to the file to replace comments in.
    comments (List[Comment]): List of comments to replace.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
        with open(file_path, 'w') as file:
            for i, line in enumerate(lines, start=1):
                for comment in comments:
                    if i == comment.line_number:
                        if comment.comment_type == 'TODO':
                            file.write(f"# TODO: {comment.comment_text}\n")
                        elif comment.comment_type == 'FIXME':
                            file.write(f"# FIXME: {comment.comment_text}\n")
                        elif comment.comment_type == 'HACK':
                            file.write(f"# HACK: {comment.comment_text}\n")
                        else:
                            file.write(line)
                        break
                else:
                    file.write(line)
    except Exception as e:
        print(f"An error occurred: {e}")

def main() -> None:
    """
    Tests the module by extracting and replacing comments in a file.
    """
    file_path = 'tools/aios_udalit_kommentarii_todofixmehack_160305.py'
    comments = extract_comments(file_path)
    print("Extracted comments:")
    for comment in comments:
        print(f"Line {comment.line_number}: {comment.comment_type} - {comment.comment_text}")
    replace_comments(file_path, comments)

if __name__ == '__main__':
    main()

__all__ = ['extract_comments', 'replace_comments']