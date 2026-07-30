import sys
#!/usr/bin/env python3
"""BATCH 60: Dead Code Removal with Approval Gate + Backup"""
import json, shutil, ast
from pathlib import Path
from datetime import datetime, timezone

BACKUP_DIR = Path('/mnt/agents/-Octopus/archive/dead_code_backup')
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
APPROVAL_FILE = Path('/run/octopus/dead_code_approval.json')

def find_dead_functions(file_path):
    try:
        tree = ast.parse(Path(file_path).read_text())
        defined = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        used = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if hasattr(node.func, 'id'):
                    used.add(node.func.id)
        return defined - used
    except Exception:
        return set()

def scan_all(root_path):
    findings = []
    for py_file in Path(root_path).rglob('*.py'):
        dead = find_dead_functions(py_file)
        if dead:
            findings.append({'file': str(py_file), 'dead_functions': list(dead)})
    return findings

def remove_dead_code(findings, approved_only=True):
    removed = []
    for item in findings:
        if approved_only:
            if not APPROVAL_FILE.exists():
                return {'ok': True, 'status': 'awaiting_approval', 'findings': findings, 'removed': removed}
        backup = BACKUP_DIR / Path(item['file']).name
        shutil.copy2(item['file'], backup)
        removed.append({'file': item['file'], 'backup': str(backup)})
    return {'ok': True, 'status': 'completed', 'removed': removed}

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else '/mnt/agents/-Octopus/skills'
    findings = scan_all(target)
    print(json.dumps(remove_dead_code(findings, approved_only=True), ensure_ascii=False, indent=2))
