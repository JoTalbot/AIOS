import hashlib

def get_signature(data):
    return hashlib.sha256(f'SECRET-KEY-{data}'.encode()).hexdigest()

def verify_remote_node(node_name, data, signature):
    expected = get_signature(data)
    if signature == expected:
        print(f'[OK] Node {node_name} signature VALID.')
        return True
    else:
        print(f'[ERROR] Node {node_name} signature INVALID!')
        return False

if __name__ == '__main__':
    master_hash = '131d23d60268a73cc85a4f94c4301ee86a3afdacc61f78081aa75da83a4d19fd'
    sig = get_signature(master_hash)
    verify_remote_node('aws-dr-node-1', master_hash, sig)
