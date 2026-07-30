import os
import json
import hashlib

VERSIONS_FILE = '/var/lib/octopus/skills_versions.json'

def get_skill_version(name):
    if not os.path.exists(VERSIONS_FILE): return "unknown"
    with open(VERSIONS_FILE, 'r') as f:
        return json.load(f).get(name, "unknown")

def sign_command(cmd, key_path='/etc/octopus/id/id_ed25519'):
    # Simple simulated signature
    return hashlib.md5(f'CMD-SIG-{cmd}'.encode()).hexdigest()
