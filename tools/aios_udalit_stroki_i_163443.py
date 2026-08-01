"""
Module for scanning Python files for TODO, FIXME, HACK, XXX and BUG tags.

Usage:
    from aios_udalit_stroki_i_163443 import scan_for_tags
    scan_for_tags(target_path='tools/aios_udalit_stroki_i_163443.py')
"""

import os
from typing import List, Dict
from aios_scanfortagsrootdir_str_listdict_115420 import scan_for_tags

__all__ = ['scan_for_tags']

def scan_for_tags_in_file(file_path: str) -> List[Dict]:
    """
    Scan a single Python file for TODO, FIXME, HACK, XXX and BUG tags.

    Args:
        file_path (str): Path to the Python file to scan.

    Returns:
        List[Dict]: List of dictionaries containing the tag name and line number.
    """
    try:
        with open(file_path, 'r') as file:
            content = file.readlines()
            return scan_for_tags(content)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []
    except Exception as e:
        print(f"Error scanning file: {file_path} - {str(e)}")
        return []

def scan_for_tags_in_directory(directory_path: str) -> List[Dict]:
    """
    Scan a directory for Python files and scan each file for TODO, FIXME, HACK, XXX and BUG tags.

    Args:
        directory_path (str): Path to the directory to scan.

    Returns:
        List[Dict]: List of dictionaries containing the tag name and line number.
    """
    try:
        files = [os.path.join(directory_path, file) for file in os.listdir(directory_path) if file.endswith('.py')]
        results = []
        for file in files:
            results.extend(scan_for_tags_in_file(file))
        return results
    except Exception as e:
        print(f"Error scanning directory: {directory_path} - {str(e)}")
        return []

def scan_for_tags_in_target_path(target_path: str) -> List[Dict]:
    """
    Scan the target path for Python files and scan each file for TODO, FIXME, HACK, XXX and BUG tags.

    Args:
        target_path (str): Path to the target directory or file.

    Returns:
        List[Dict]: List of dictionaries containing the tag name and line number.
    """
    if os.path.isfile(target_path):
        return scan_for_tags_in_file(target_path)
    elif os.path.isdir(target_path):
        return scan_for_tags_in_directory(target_path)
    else:
        print(f"Invalid target path: {target_path}")
        return []

if __name__ == '__main__':
    target_path = 'tools/aios_udalit_stroki_i_163443.py'
    results = scan_for_tags_in_target_path(target_path)
    print(results)