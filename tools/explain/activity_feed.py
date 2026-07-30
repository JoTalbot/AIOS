#!/usr/bin/env python3
"""Octopus Activity Feed (Instruction #55)"""
import json, os
from datetime import datetime, timezone

FEED_FILE = '/mnt/agents/-Octopus/data/activity_feed.jsonl'

def log_action(action, details=None):
    entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'action': action,
        'details': details or {}
    }
    with open(FEED_FILE, 'a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return entry

def get_feed(limit=50):
    if not os.path.exists(FEED_FILE):
        return []
    entries = []
    with open(FEED_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries[-limit:]

if __name__ == '__main__':
    log_action('batch_executed', {'batches': 15})
    print(json.dumps({'ok': True, 'feed': get_feed(5)}, ensure_ascii=False, indent=2))
