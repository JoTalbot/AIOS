import hashlib
import os

def calculate_master_hash(pool_path='/var/lib/octopus/packstore'):
    """Compute a master SHA-256 hash over all files in the packstore pool.

    Args:
        pool_path: Directory of the packstore pool to walk.

    Returns:
        Hex digest of the combined per-file SHA-256 hashes, or ``"0000"``
        when ``pool_path`` does not exist.
    """
    hashes = []
    if not os.path.exists(pool_path): return "0000"
    for root, dirs, files in os.walk(pool_path):
        for f in sorted(files):
            p = os.path.join(root, f)
            with open(p, 'rb') as file:
                hashes.append(hashlib.sha256(file.read()).hexdigest())
    return hashlib.sha256(''.join(hashes).encode()).hexdigest()
