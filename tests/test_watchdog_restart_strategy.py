#!/usr/bin/env python3
import importlib.util
from unittest import mock

import os
import pytest

if not os.path.exists('/opt/octopus-watchdog.py'):
    pytest.skip('/opt/octopus-watchdog.py отсутствует на этом хосте', allow_module_level=True)

spec = importlib.util.spec_from_file_location('octopus_watchdog', '/opt/octopus-watchdog.py')
wd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wd)


def test_localhost_check_is_tcp_only_no_api():
    node = {'ip':'127.0.0.1','port':12345,'label':'local-child','check_type':'api'}
    with mock.patch.object(wd, '_tcp_open', return_value=True), \
         mock.patch.object(wd.urllib.request, 'urlopen', side_effect=AssertionError('API must not be called for localhost')):
        assert wd.check_node(node) == ('ok', 'tcp_only/local')


def test_localhost_restart_never_ssh():
    node = {'ip':'127.0.0.1','port':12345,'label':'local-child','ssh_key':'/etc/hosts','restart_strategy':'ssh_remote'}
    with mock.patch.object(wd.subprocess, 'run', side_effect=AssertionError('ssh must not be called')):
        ok, reason = wd.restart_node(node)
    assert ok is False
    assert 'local/tunnel' in reason


def test_registry_restart_strategy_none_blocks_restart():
    node = {'ip':'203.0.113.10','port':9100,'label':'disabled-node','ssh_key':'/etc/hosts','restart_strategy':'none'}
    with mock.patch.object(wd.subprocess, 'run', side_effect=AssertionError('ssh must not be called')):
        ok, reason = wd.restart_node(node)
    assert ok is False
    assert 'strategy=none' in reason


def test_ssh_remote_uses_explicit_user_and_command():
    node = {
        'ip':'203.0.113.10','port':9100,'label':'remote-node',
        'ssh_key':'/etc/hosts','ssh_user':'ubuntu','ssh_enabled':True,
        'restart_strategy':'ssh_remote','restart_command':'echo active && systemctl is-active octopus.service'
    }
    class R:
        returncode = 0
        stdout = 'active\n'
        stderr = ''
    with mock.patch.object(wd.subprocess, 'run', return_value=R()) as run:
        ok, reason = wd.restart_node(node)
    assert ok is True
    argv = run.call_args[0][0]
    assert 'ubuntu@203.0.113.10' in argv
    assert argv[-1] == node['restart_command']

if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
            print('PASS', name)

def test_http_json_health_url_skips_tcp():
    node = {"ip":"example.invalid","port":0,"label":"http-node","check_type":"http_json","health_url":"https://example.invalid/health"}
    class R:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self, n=-1): return b"{\"status\":\"ok\"}"
    with mock.patch.object(wd, "_tcp_open", side_effect=AssertionError("tcp must not be called")), \
         mock.patch.object(wd.urllib.request, "urlopen", return_value=R()):
        assert wd.check_node(node) == ("ok", "http 200")
