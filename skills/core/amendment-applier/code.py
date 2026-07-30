import os
import json

AMENDMENTS_FILE = '/var/lib/octopus/suggested_amendments.json'
INSTR_ROOT = '/root/agents'

def apply_amendments():
    if not os.path.exists(AMENDMENTS_FILE): return
    with open(AMENDMENTS_FILE, 'r') as f:
        amendments = json.load(f)
    
    for a in amendments:
        path = os.path.join(INSTR_ROOT, a['target_file'])
        if os.path.exists(path):
            with open(path, 'a') as f:
                f.write(f'\n# AMENDMENT 2026-06-20: {a["amendment"]}\n')
            print(f'[APPLIED] Amendment added to {a["target_file"]}')

if __name__ == '__main__':
    apply_amendments()
