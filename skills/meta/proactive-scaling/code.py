import os
import sys
import subprocess

def scale_up_node(node_id):
    print(f'[PROACTIVE] Scaling up resources for {node_id} based on forecast...')
    if node_id == 'ubu-worker-8400':
        # Simulated scaling: increasing worker priority or reserved RAM
        # In reality: ssh ... 'systemctl restart octopus-whisper-worker --increase-priority'
        print('[OK] Resources reserved on ubu-worker.')

if __name__ == '__main__':
    scale_up_node('ubu-worker-8400')
