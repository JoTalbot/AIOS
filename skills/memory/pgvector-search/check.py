#!/usr/bin/env python3
import json, subprocess

def check_pgvector():
    try:
        r = subprocess.run(['sudo', '-u', 'postgres', 'psql', '-c', 'CREATE EXTENSION IF NOT EXISTS vector;'],
                          capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return {'ok': True, 'status': 'available'}
        return {'ok': False, 'status': 'failed', 'error': r.stderr}
    except Exception as e:
        return {'ok': False, 'status': 'error', 'error': str(e)}

if __name__ == '__main__':
    print(json.dumps(check_pgvector(), ensure_ascii=False, indent=2))
