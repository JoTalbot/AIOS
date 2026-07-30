#!/usr/bin/env python3
"""BATCH 71: End-to-end integration tests"""
import json, subprocess, sys
from datetime import datetime, timezone

def run_test(name, command, expected_in_output=None):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30, shell=True)
        ok = result.returncode == 0
        if expected_in_output:
            ok = ok and expected_in_output in result.stdout
        return {'test': name, 'ok': ok, 'output': result.stdout[:200]}
    except Exception as e:
        return {'test': name, 'ok': False, 'error': str(e)}

if __name__ == '__main__':
    tests = [
        run_test('lead_pipeline_health', 'curl -s http://127.0.0.1:8095/health', 'ok'),
        run_test('webdav_health', 'curl -s http://127.0.0.1:8096/health', 'ok'),
        run_test('ipfs_health', 'curl -s -X POST http://127.0.0.1:5001/api/v0/version', 'Version'),
        run_test('pwa_health', 'curl -s http://127.0.0.1/ | grep -o Octopus', 'Octopus'),
        run_test('slo_green', 'python3 /opt/octopus-slo-checker.py', 'fail": 0'),
        run_test('ollama_health', 'curl -s http://127.0.0.1:11434/api/tags', 'models'),
        run_test('memory_search', 'python3 /mnt/agents/-Octopus/skills/memory/semantic_search/main.py тест', 'ok'),
        run_test('cli_status', '/mnt/agents/-Octopus/tools/cli/octopus status', 'ok'),
    ]
    passed = sum(1 for t in tests if t['ok'])
    print(json.dumps({'ok': passed == len(tests), 'passed': passed, 'total': len(tests), 'tests': tests}, ensure_ascii=False, indent=2))
