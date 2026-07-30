#!/usr/bin/env python3
"""BATCH 44: Auto-Heal Config Drift Correction"""
import json, hashlib, shutil
from pathlib import Path
from datetime import datetime, timezone

SNAPSHOT_DIR = Path('/run/octopus/config_snapshots')
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

def restore_config(file_path):
    snapshot = SNAPSHOT_DIR / Path(file_path).name.replace('/', '_')
    if snapshot.exists():
        shutil.copy2(snapshot, file_path)
        return {'ok': True, 'restored': file_path}
    return {'ok': False, 'error': 'no_snapshot'}

def detect_and_heal():
    import sys
    sys.path.insert(0, '/mnt/agents/-Octopus/skills/core/autoheal')
    from config_drift import detect_drift
    report = detect_drift()
    healed = []
    for item in report.get('drift', []):
        if item.get('status') == 'drift_detected':
            result = restore_config(item['file'])
            healed.append({'file': item['file'], 'result': result})
    return {'ok': True, 'healed': healed, 'timestamp': datetime.now(timezone.utc).isoformat()}

if __name__ == '__main__':
    print(json.dumps(detect_and_heal(), ensure_ascii=False, indent=2))
