#!/usr/bin/env python3
import importlib.util

import os
import pytest

if not os.path.exists('/opt/octopus_dr_config.py'):
    pytest.skip('/opt/octopus_dr_config.py отсутствует на этом хосте', allow_module_level=True)

spec = importlib.util.spec_from_file_location('octopus_dr_config', '/opt/octopus_dr_config.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_all_scope_has_expected_children():
    result = mod.check_scope('all')
    assert result['ok'] is True
    assert set(result['checks'].keys()) == {
        'memory_restore_drill',
        'memory_manifest',
        'memory_restore_drill_ec2',
        'snapshot',
        'bootstrap',
    }


def test_snapshot_scope_has_only_non_secret_fields_and_policy_flag():
    result = mod.check_scope('snapshot')
    cfg = result['config']
    assert set(cfg.keys()) == {
        'HF_REPO_ID', 'HF_TOKEN_PRESENT', 'TG_BOT_TOKEN_PRESENT', 'TG_CHAT_ID_PRESENT',
        'S3_BUCKET', 'SNAPSHOT_DIR', 'SNAPSHOT_ARCHIVE', 'DR_MANIFEST', 'CHUNK_SIZE_MB',
        'KEEP_LOCAL_ARCHIVE', 'OCTOPUS_PUBLIC_IP', 'TG_ARCHIVE_DIRECT_DISABLED'
    }
    assert cfg['TG_ARCHIVE_DIRECT_DISABLED'] is True


def test_bootstrap_scope_has_manifest_url_and_policy_flag():
    result = mod.check_scope('bootstrap')
    cfg = result['config']
    assert cfg['MANIFEST_URL'].startswith('https://huggingface.co/datasets/')
    assert cfg['DIRECT_TELEGRAM_NOTIFY_DISABLED'] is True


def test_schema_for_bootstrap_contains_expected_fields():
    schema = mod.get_scope_schema('bootstrap')
    names = {field['name'] for field in schema['fields']}
    assert {'HF_REPO', 'HF_BASE', 'MANIFEST_URL', 'S3_BUCKET', 'AWS_CREDENTIALS_PRESENT', 'DIRECT_TELEGRAM_NOTIFY_DISABLED'} <= names


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
            print('PASS', name)
