import csv
import os
from datetime import datetime

LEDGER_FILE = '/var/lib/octopus/barter_ledger.csv'

def log_transaction(swarm_id, resource, amount, direction='export'):
    fieldnames = ['timestamp', 'partner', 'resource', 'amount', 'direction']
    file_exists = os.path.isfile(LEDGER_FILE)
    
    with open(LEDGER_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            'timestamp': datetime.now().isoformat(),
            'partner': swarm_id,
            'resource': resource,
            'amount': amount,
            'direction': direction
        })
    print(f'[LEDGER] Transaction logged: {amount} {resource} {direction}ed to/from {swarm_id}')

if __name__ == '__main__':
    log_transaction('swarm-beta-99', 'whisper_hours', 1.5, 'export')
