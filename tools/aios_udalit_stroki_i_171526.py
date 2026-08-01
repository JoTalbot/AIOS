import os
import re
from dataclasses import dataclass
from typing import List

@dataclass
class Tag:
    """Dataclass to represent a tag."""
    line_number: int
    tag: str

    def __post_init__(self):
        """Initialize the tag."""
        self.line_number = int(self.line_number)

def scan_python_files(path: str) -> List[Tag]:
    """
    Scan Python files in the given path for TODO/FIXME/HACK tags.

    Args:
    path (str): The path to scan.

    Returns:
    List[Tag]: A list of tags found in the files.
    """
    tags = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith('.py'):
                try:
                    with open(os.path.join(root, file), 'r') as f:
                        content = f.readlines()
                        for i, line in enumerate(content, start=1):
                            match = re.search(r'\b(TODO|FIXME|HACK)\b', line)
                            if match:
                                tags.append(Tag(line_number=i, tag=match.group()))
                except Exception as e:
                    print(f"Error scanning file {file}: {e}")
    return tags

def main():
    """Main function."""
    path = 'tools'
    tags = scan_python_files(path)
    for tag in tags:
        print(f"Line {tag.line_number}: {tag.tag}")

if __name__ == '__main__':
    main()
    __all__ = ['scan_python_files']