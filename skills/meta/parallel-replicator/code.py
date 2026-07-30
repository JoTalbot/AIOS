import sys
sys.path.append('/root/agents/-Octopus/lib')
from node_helpers import get_node_power

def decide_sync_path(parent_load):
    print(f'[REPLICATOR] Evaluating swarm topology. Parent load: {parent_load}')
    if float(parent_load) > 1.5:
        print('[DECISION] Parent busy. Offloading sync to AWS-DR-Node-1.')
        return 'AWS -> UBU'
    else:
        print('[DECISION] Parent healthy. Direct sync active.')
        return 'PARENT -> ALL'

if __name__ == '__main__':
    decide_sync_path(0.2)
