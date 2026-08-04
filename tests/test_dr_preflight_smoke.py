#!/usr/bin/env python3
import json
import subprocess
import os
import pytest

if not os.path.exists('/root/agents/-Octopus/scripts/dr_config_preflight.py'):
    pytest.skip('octopus runtime не установлен на этом хосте', allow_module_level=True)



def _json_from_cmd(cmd):
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out)


def test_unified_preflight_all_ok():
    data = _json_from_cmd(['python3', '/root/agents/-Octopus/scripts/dr_config_preflight.py', '--scope', 'all', '--json'])
    assert data['ok'] is True
    assert data['result']['ok'] is True


def test_preflight_schema_all_ok():
    data = _json_from_cmd(['python3', '/root/agents/-Octopus/scripts/dr_config_preflight.py', '--scope', 'all', '--schema', '--json'])
    assert data['ok'] is True
    assert data['scope'] == 'all'
    assert 'schemas' in data['result']


def test_bootstrap_preflight_ok():
    data = _json_from_cmd(['bash', '/opt/octopus/octopus-bootstrap.sh', '--preflight'])
    assert data['ok'] is True
    assert data['scope'] == 'bootstrap'


def test_skill_runtime_preflight_ok():
    data = _json_from_cmd(['python3', '/root/agents/-Octopus/skills/core/dr-config-preflight/code/run.py', '--scope', 'all', '--json'])
    assert data['ok'] is True
    assert data['result']['ok'] is True


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
            print('PASS', name)
