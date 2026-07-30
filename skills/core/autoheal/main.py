#!/usr/bin/env python3
"""BATCH 36: Auto-Heal Dead Code Detection"""
import os, ast, json
from pathlib import Path
from datetime import datetime, timezone

def find_dead_code(root_path: str):
    dead = []
    for py_file in Path(root_path).rglob('*.py'):
        try:
            tree = ast.parse(py_file.read_text())
            defined = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
            used = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if hasattr(node.func, 'id'):
                        used.add(node.func.id)
            unused = defined - used
            if unused:
                dead.append({'file': str(py_file), 'unused_functions': list(unused)})
        except Exception:
            pass
    return {'ok': True, 'dead_code': dead, 'scanned_at': datetime.now(timezone.utc).isoformat()}

if __name__ == '__main__':
    result = find_dead_code('/mnt/agents/-Octopus/skills')
    print(json.dumps(result, ensure_ascii=False, indent=2))
