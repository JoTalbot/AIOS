import os
import subprocess

def optimize():
    print('[RESOURCE-OPTIMIZER] Checking system load...')
    load = os.getloadavg()[0]
    if load > 4.0:
        print(f'High load detected: {load}. Pausing non-critical background tasks...')
        # Logic to pause intensive tasks like whisper if running locally
        subprocess.run(['systemctl', 'stop', 'octopus-whisper-worker.service'])
    else:
        print(f'Load normal: {load}. Ensuring workers are active.')
        subprocess.run(['systemctl', 'start', 'octopus-whisper-worker.service'])

if __name__ == '__main__':
    optimize()
