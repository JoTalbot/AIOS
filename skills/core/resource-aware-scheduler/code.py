import json
import os

STORAGE_REPORT = '/var/lib/octopus/reports/storage_health_2026-06-20.json'

def get_best_node():
    if not os.path.exists(STORAGE_REPORT):
        return 'parent'
    
    with open(STORAGE_REPORT, 'r') as f:
        data = json.load(f)
    
    # Simple logic: choose node with most free space (parsing strings like '67G')
    nodes = data.get('nodes', {})
    best_node = 'parent'
    max_free = 0
    
    for name, info in nodes.items():
        free_str = info.get('free_space', '0').split()[0]
        try:
            # Very basic conversion for simulation
            val = float(free_str.replace('G', '').replace('M', ''))
            if 'G' in free_str: val *= 1024
            if val > max_free:
                max_free = val
                best_node = name
        except: continue
        
    print(f'[SCHEDULER] Recommendation: Launch heavy task on {best_node}')
    return best_node

if __name__ == '__main__':
    get_best_node()
