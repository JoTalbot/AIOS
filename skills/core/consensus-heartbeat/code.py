import subprocess
import time
import os

def run_heartbeat():
    print(f'[HEARTBEAT] Cycle started at {time.strftime("%Y-%m-%d %H:%M:%S")}')
    try:
        # Trigger validation
        res = subprocess.check_output(['python3', '/root/agents/-Octopus/skills/core/self-replication-validator/code.py'], text=True)
        print(res)
        # Log to event bus
        os.system(f'python3 /opt/octopus-nostr-relay-shim.py "Consensus Heartbeat: OK"')
    except Exception as e:
        print(f'[ERROR] Heartbeat failed: {e}')

if __name__ == '__main__':
    run_heartbeat()
