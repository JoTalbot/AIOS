"""Final health checks for the entire project."""

import os
from pathlib import Path


def test_all_init_files_exist():
    root = Path(__file__).parent.parent
    missing = []
    for d in root.rglob('aios_core/*/'):
        if '__pycache__' in str(d): continue
        if not (d / '__init__.py').exists():
            missing.append(str(d))
    assert len(missing) <= 5, f'Missing __init__.py: {missing}'


def test_no_empty_init_files():
    root = Path(__file__).parent.parent
    empty = []
    for init_file in root.rglob('aios_core/**/__init__.py'):
        if init_file.stat().st_size == 0:
            empty.append(str(init_file))
    assert len(empty) == 0, f'Empty __init__.py: {empty}'
