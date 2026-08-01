"""
Module for scanning secrets in project files.

Exports:
    - scan_for_tags: scans secrets in project files
    - test_scan_for_tags: tests the scan_for_tags function
"""

import os
from aios_scanfortagsrootdir_str_listdict_115420 import scan_for_tags as _scan_for_tags

__all__ = ['scan_for_tags', 'test_scan_for_tags']

async def scan_for_tags(root_dir: str) -> dict[str, list[str]]:
    """
    Scans secrets in project files.

    Args:
        root_dir: The root directory to scan for secrets.

    Returns:
        A dictionary with file paths as keys and lists of secrets as values.
    """
    try:
        return await _scan_for_tags(root_dir)
    except Exception as e:
        print(f"Error scanning for secrets: {e}")
        return {}

async def test_scan_for_tags() -> None:
    """
    Tests the scan_for_tags function.
    """
    root_dir = os.path.dirname(__file__)
    secrets = await scan_for_tags(root_dir)
    print("Scanned secrets:")
    for file, tags in secrets.items():
        print(f"  {file}: {tags}")

if __name__ == '__main__':
    import asyncio
    asyncio.run(test_scan_for_tags())