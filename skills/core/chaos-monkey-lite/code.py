import random
import subprocess
import time

def kill_random_child():
    child_id = random.randint(8300, 8302) # Start with safe range
    print(f'[CHAOS] Killing child process on port {child_id}...')
    # Logic to find and kill process or stop systemd unit
    cmd = f'systemctl stop octopus-child@{child_id}.service'
    print(f'Running: {cmd}')
    # For now, dry-run safety
    print('[CHAOS] Simulation complete. Autoheal should detect this.')

if __name__ == '__main__':
    kill_random_child()
