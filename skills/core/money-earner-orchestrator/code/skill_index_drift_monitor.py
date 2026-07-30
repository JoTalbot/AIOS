#!/usr/bin/env python3
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

B = Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator')
D = B / 'data'
cmd = ['/usr/bin/python3', str(B / 'code/skill_index_rebuilder.py'), '--check']
proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
try:
    payload = json.loads(proc.stdout)
except Exception:
    payload = {
        'changed': None,
        'parse_error': True,
        'stdout_tail': proc.stdout[-2000:],
        'stderr_tail': proc.stderr[-2000:],
    }
healthy = proc.returncode == 0 and payload.get('changed') is False
out = {
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'mode': 'read_only_skill_index_drift_monitor',
    'healthy': healthy,
    'check_exit_code': proc.returncode,
    'changed': payload.get('changed'),
    'applied': False,
    'audit': payload.get('audit', {}),
    'details': payload,
}
D.mkdir(parents=True, exist_ok=True)
(D / 'skill_index_drift_latest.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'healthy': healthy, 'changed': out['changed'], 'check_exit_code': proc.returncode}, ensure_ascii=False))
# Always exit 0 so the timer remains a reporting mechanism; runtime health consumes healthy/changed.
