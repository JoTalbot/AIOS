import subprocess
import os
import sys
sys.path.append('/root/agents/-Octopus/lib')
from node_helpers import get_node_power

def validate():
    print('--- Octopus BFT Validation (Using Lib) ---')
    power = get_node_power('parent')
    print(f'Parent weight verified: {power}')

if __name__ == '__main__':
    validate()
