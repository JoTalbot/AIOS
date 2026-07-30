import os
import shutil
from datetime import datetime

QUARANTINE_DIR = '/var/lib/octopus/quarantine'

def quarantine_orphans():
    os.makedirs(QUARANTINE_DIR, exist_ok=True)
    candidates = ['/tmp/found_audio.txt', '/tmp/aws_launch_result.json'] # From previous batches
    for item in candidates:
        if os.path.exists(item):
            dest = os.path.join(QUARANTINE_DIR, os.path.basename(item))
            shutil.move(item, dest)
            print(f'[QUARANTINE] Moved to recovery zone: {item}')
    print('[OK] Orphans quarantined for 24h evaluation.')

if __name__ == '__main__':
    quarantine_orphans()
