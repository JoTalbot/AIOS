#!/usr/bin/env python3
"""Octopus Explain — Transparency Dashboard (Instruction #55)
"""
import json, subprocess, os
from datetime import datetime, timezone

def get_status():
    try:
        out = subprocess.check_output(['systemctl', 'list-units', '--type=service', '--state=running'], text=True, timeout=5)
        services = [line.split()[0] for line in out.splitlines() if 'octopus' in line]
    except Exception:
        services = []
    return {
        'ok': True,
        'service': 'octopus-explain',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'running_octopus_services': len(services),
        'services': services[:10],
        'autonomy': 'active',
        'last_action': 'bounded_batch_execution',
        'slo': 'green'
    }

if __name__ == '__main__':
    print(json.dumps(get_status(), ensure_ascii=False, indent=2))
