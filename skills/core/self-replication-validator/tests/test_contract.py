#!/usr/bin/env python3
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR / 'code'))
from self_replication_validator import run

def test_run_returns_dict():
    payload = run('')
    assert isinstance(payload, dict)
    assert payload['skill'] == 'self-replication-validator'
    assert 0 <= payload['score'] <= 1000
    assert 'grade' in payload
    print('test_run_returns_dict: OK')

if __name__ == '__main__':
    test_run_returns_dict()
    print('All tests passed!')
