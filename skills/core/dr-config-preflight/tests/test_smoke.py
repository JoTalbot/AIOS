#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]


def test_skill_run_all_scope_json_ok():
    out = subprocess.check_output(['python3', str(SKILL_DIR / 'code' / 'run.py'), '--scope', 'all', '--json'], text=True)
    data = json.loads(out)
    assert data['ok'] is True
    assert data['result']['ok'] is True


def test_skill_schema_snapshot_json_ok():
    out = subprocess.check_output(['python3', str(SKILL_DIR / 'code' / 'run.py'), '--scope', 'snapshot', '--schema', '--json'], text=True)
    data = json.loads(out)
    assert data['ok'] is True
    assert data['scope'] == 'snapshot'
    assert 'result' in data and 'fields' in data['result']


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
            print('PASS', name)
