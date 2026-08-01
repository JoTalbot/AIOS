from aios_scanfortagsrootdir_str_listdict_115420 import scan_for_tags
from dataclasses import dataclass
from pathlib import Path
from typing import List

__all__ = ['scan_project_for_tags']

@dataclass
class TaggedFile:
    """Dataclass to hold information about a tagged file."""
    path: Path
    tags: List[str]

async def scan_project_for_tags(root_dir: Path) -> List[TaggedFile]:
    """
    Scan all files in the project for TODO/FIXME/HACK tags and return a list of tagged files.

    Args:
    root_dir: The root directory of the project to scan.

    Returns:
    A list of TaggedFile objects containing the path and tags of each file.
    """
    try:
        tagged_files = await scan_for_tags(root_dir)
        return tagged_files
    except Exception as e:
        print(f"Error scanning project for tags: {e}")
        return []

if __name__ == '__main__':
    root_dir = Path('tools')
    tagged_files = scan_project_for_tags(root_dir)
    for file in tagged_files:
        print(f"File: {file.path}, Tags: {file.tags}")