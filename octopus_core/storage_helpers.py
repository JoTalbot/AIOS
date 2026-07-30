import hashlib
import os

def calculate_master_hash(pool_path='/var/lib/octopus/packstore'):
    hashes = []
    if not os.path.exists(pool_path): return "0000"
    for root, dirs, files in os.walk(pool_path):
        for f in sorted(files):
            p = os.path.join(root, f)
            with open(p, 'rb') as file:
                hashes.append(hashlib.sha256(file.read()).hexdigest())
    return hashlib.sha256(''.join(hashes).encode()).hexdigest()
