#!/usr/bin/env python3
"""BATCH 39: Config Drift Detection for Auto-Heal"""
import json, hashlib, os
from pathlib import Path
from datetime import datetime, timezone

CONFIG_FILES = [
    '/etc/octopus/secrets.env',
    '/etc/systemd/system/octopus-lead-pipeline.service',
    '/etc/systemd/system/octopus-webdav.service',
    '/etc/systemd/system/octopus-health-cascade.timer',
]

SNAPSHOT_DIR = Path('/run/octopus/config_snapshots')
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

def file_hash(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except Exception:
        return None

def detect_drift():
    drift = []
    for cfg in CONFIG_FILES:
        current_hash = file_hash(cfg)
        snapshot_path = SNAPSHOT_DIR / Path(cfg).name.replace('/', '_')
        if snapshot_path.exists():
            baseline_hash = snapshot_path.read_text().strip()
            if current_hash != baseline_hash:
                drift.append({'file': cfg, 'baseline': baseline_hash, 'current': current_hash, 'status': 'drift_detected'})
        else:
            snapshot_path.write_text(current_hash or '')
            drift.append({'file': cfg, 'status': 'new_baseline'})
    return {'ok': True, 'drift': drift, 'checked_at': datetime.now(timezone.utc).isoformat()}

if __name__ == '__main__':
    print(json.dumps(detect_drift(), ensure_ascii=False, indent=2))
