from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_MAX_HASH_BYTES = 1024 * 1024


@dataclass(frozen=True)
class StorageProof:
    target: str
    backend: str
    path: str
    exists: bool
    readable: bool
    kind: str
    size_bytes: int | None
    sample_sha256: str | None
    sampled_bytes: int
    child_count_sample: int | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.exists and self.readable and self.error is None


def _safe_hash_file(path: Path, max_bytes: int = DEFAULT_MAX_HASH_BYTES) -> tuple[str | None, int, str | None]:
    try:
        h = hashlib.sha256()
        sampled = 0
        with path.open('rb') as fh:
            while sampled < max_bytes:
                chunk = fh.read(min(65536, max_bytes - sampled))
                if not chunk:
                    break
                h.update(chunk)
                sampled += len(chunk)
        return h.hexdigest(), sampled, None
    except Exception as exc:  # pragma: no cover - exact OS errors vary
        return None, 0, f'{type(exc).__name__}: {exc}'


def _sample_dir(path: Path, limit: int = 50) -> tuple[int | None, str | None]:
    try:
        count = 0
        for _ in path.iterdir():
            count += 1
            if count >= limit:
                break
        return count, None
    except Exception as exc:  # pragma: no cover
        return None, f'{type(exc).__name__}: {exc}'


def prove_path(target: str, max_hash_bytes: int = DEFAULT_MAX_HASH_BYTES) -> StorageProof:
    if ':' in target:
        backend, raw_path = target.split(':', 1)
    else:
        backend, raw_path = 'local_path', target
    path = Path(raw_path)
    try:
        exists = path.exists()
        if not exists:
            return StorageProof(target, backend, str(path), False, False, 'missing', None, None, 0, None, 'missing')
        st = path.stat()
        if path.is_file():
            digest, sampled, err = _safe_hash_file(path, max_bytes=max_hash_bytes)
            return StorageProof(target, backend, str(path), True, err is None, 'file', st.st_size, digest, sampled, None, err)
        if path.is_dir():
            count, err = _sample_dir(path)
            return StorageProof(target, backend, str(path), True, err is None, 'directory', None, None, 0, count, err)
        return StorageProof(target, backend, str(path), True, os.access(path, os.R_OK), 'other', st.st_size, None, 0, None, None)
    except Exception as exc:  # pragma: no cover
        return StorageProof(target, backend, str(path), False, False, 'error', None, None, 0, None, f'{type(exc).__name__}: {exc}')


def prove_many(targets: Iterable[str], max_hash_bytes: int = DEFAULT_MAX_HASH_BYTES) -> dict:
    proofs = [prove_path(t, max_hash_bytes=max_hash_bytes) for t in targets]
    return {
        'dry_run': True,
        'read_only': True,
        'destructive_ops': 0,
        'write_ops': 0,
        'delete_ops': 0,
        'gc_ops': 0,
        'target_count': len(proofs),
        'ok_count': sum(1 for p in proofs if p.ok),
        'error_count': sum(1 for p in proofs if not p.ok),
        'proofs': [asdict(p) | {'ok': p.ok} for p in proofs],
    }


def to_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
