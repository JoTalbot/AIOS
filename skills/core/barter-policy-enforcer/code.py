import csv
import os

LEDGER_FILE = '/var/lib/octopus/barter_ledger.csv'
DEBT_LIMIT = -5.0 # Max 5 units of debt

def check_balance(swarm_id):
    balance = 0.0
    if not os.path.exists(LEDGER_FILE): return balance
    
    with open(LEDGER_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['partner'] == swarm_id:
                amount = float(row['amount'])
                if row['direction'] == 'export': balance += amount
                else: balance -= amount
    
    print(f'[POLICY] Balance for {swarm_id}: {balance}')
    return balance

def is_service_allowed(swarm_id):
    balance = check_balance(swarm_id)
    if balance < DEBT_LIMIT:
        print(f'[REJECT] Service denied for {swarm_id}. Debt too high.')
        return False
    return True

if __name__ == '__main__':
    is_service_allowed('swarm-beta-99')
