import json
import os

REPUTATION_DB = '/var/lib/octopus/reputation.json'

def get_voting_power(node_id):
    if not os.path.exists(REPUTATION_DB): return 1.0
    with open(REPUTATION_DB, 'r') as f:
        data = json.load(f)
    
    score = data.get(node_id, {}).get('score', 0)
    # Power = 1 + (score / 100)
    return round(1.0 + (score / 100.0), 2)

if __name__ == '__main__':
    print(f'Parent voting power: {get_voting_power("parent")}')
