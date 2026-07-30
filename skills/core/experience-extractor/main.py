#!/usr/bin/env python3
"""BATCH 49: Experience Extraction from Logs"""
import json
from pathlib import Path
from datetime import datetime, timezone

LOG_DIR = Path('/mnt/agents/-Octopus/logs')
EXP_DIR = Path('/mnt/agents/-Octopus/experience')
EXP_DIR.mkdir(parents=True, exist_ok=True)

def extract_experiences(limit=20):
    experiences = []
    if LOG_DIR.exists():
        for log_file in sorted(LOG_DIR.glob('*.log'))[-limit:]:
            try:
                content = log_file.read_text(errors='ignore')
                experiences.append({
                    'source': str(log_file.name),
                    'type': 'log',
                    'size': len(content),
                    'extracted_at': datetime.now(timezone.utc).isoformat()
                })
            except Exception:
                pass
    return {'ok': True, 'experiences': experiences, 'count': len(experiences)}

if __name__ == '__main__':
    print(json.dumps(extract_experiences(), ensure_ascii=False, indent=2))
