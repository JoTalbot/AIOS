import json
import os
import time

REPUTATION_DB = '/var/lib/octopus/reputation.json'

def update_reputation(node_id, increment):
    data = {}
    if os.path.exists(REPUTATION_DB):
        try:
            with open(REPUTATION_DB, 'r') as f: data = json.load(f)
        except: pass
    
    node_data = data.get(node_id, {'score': 0, 'uptime_hours': 0})
    node_data['score'] += increment
    node_data['last_seen'] = int(time.time())
    if increment > 0: # Simple way to track uptime increments
        node_data['uptime_hours'] = node_data.get('uptime_hours', 0) + 1
    data[node_id] = node_data
    
    with open(REPUTATION_DB, 'w') as f:
        json.dump(data, f, indent=2)
    print(f'[REPUTATION] Node {node_id} updated. Score: {node_data["score"]}, Uptime: {node_data.get("uptime_hours")}h')

if __name__ == '__main__':
    # Test reward
    update_reputation('parent', 1)
