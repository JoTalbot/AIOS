import json
import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(
    not os.path.exists('scripts/octopus-storage-live-read-proof.py'),
    reason='octopus-storage-live-read-proof.py отсутствует на этом хосте',
)

from swarm.ops.storage_live_read_proof import prove_many, prove_path


def test_prove_file_hashes_sample(tmp_path):
    f = tmp_path / 'sample.txt'
    f.write_text('octopus-proof')
    proof = prove_path(f'local_path:{f}')
    assert proof.ok is True
    assert proof.kind == 'file'
    assert proof.sampled_bytes == len('octopus-proof')
    assert proof.sample_sha256


def test_prove_directory_lists_sample(tmp_path):
    (tmp_path / 'a').write_text('a')
    proof = prove_path(f'garage_dir:{tmp_path}')
    assert proof.ok is True
    assert proof.kind == 'directory'
    assert proof.child_count_sample == 1


def test_prove_many_is_read_only(tmp_path):
    f = tmp_path / 'sample.txt'
    f.write_text('x')
    payload = prove_many([f'local_path:{f}'])
    assert payload['read_only'] is True
    assert payload['destructive_ops'] == 0
    assert payload['write_ops'] == 0
    assert payload['delete_ops'] == 0
    assert payload['gc_ops'] == 0
    assert payload['ok_count'] == 1


def test_cli_json_with_explicit_target(tmp_path):
    f = tmp_path / 'sample.txt'
    f.write_text('x')
    result = subprocess.run(
        [sys.executable, 'scripts/octopus-storage-live-read-proof.py', '--json', '--target', f'local_path:{f}'],
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(result.stdout)
    assert payload['read_only'] is True
    assert payload['ok_count'] == 1
    assert payload['proofs'][0]['ok'] is True
