import json
import os

REPUTATION_DB = '/var/lib/octopus/reputation.json'

def get_sync_order():
    if not os.path.exists(REPUTATION_DB): return []
    with open(REPUTATION_DB, 'r') as f:
        data = json.load(f)
    # Higher score = earlier sync
    sorted_nodes = sorted(data.items(), key=lambda x: x[1]['score'], reverse=True)
    return [node for node, info in sorted_nodes]

if __name__ == '__main__':
    order = get_sync_order()
    print(f'[PRIORITY-SYNC] Recommended sync order: {" -> ".join(order)}')
