#!/usr/bin/env python3
import json
import subprocess
import os
import pytest

if not os.path.exists('/opt/octopus-memory-restore-drill.py'):
    pytest.skip('octopus runtime не установлен на этом хосте', allow_module_level=True)



def _run_json(cmd):
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out)


def test_memory_restore_drill_check_config_ok():
    data = _run_json(['python3', '/opt/octopus-memory-restore-drill.py', '--check-config'])
    assert data['ok'] is True
    assert data['scope'] == 'memory_restore_drill'


def test_memory_manifest_check_config_ok():
    data = _run_json(['python3', '/opt/octopus-memory-manifest.py', '--check-config'])
    assert data['ok'] is True
    assert data['scope'] == 'memory_manifest'


def test_memory_restore_drill_ec2_check_config_ok():
    data = _run_json(['python3', '/opt/octopus-memory-restore-drill-ec2.py', '--check-config'])
    assert data['ok'] is True
    assert data['scope'] == 'memory_restore_drill_ec2'


def test_snapshot_check_config_json_ok():
    data = _run_json(['python3', '/opt/octopus/octopus-eternal-snapshot.py', '--check-config-json'])
    assert data['ok'] is True
    assert data['scope'] == 'snapshot'


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
            print('PASS', name)
