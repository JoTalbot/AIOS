import os
import json
import hashlib

SKILLS_ROOT = '/root/agents/-Octopus/skills'
VERSIONS_FILE = '/var/lib/octopus/skills_versions.json'

def update_versions():
    versions = {}
    for root, dirs, files in os.walk(SKILLS_ROOT):
        if 'SKILL.md' in files:
            name = os.path.basename(root)
            with open(os.path.join(root, 'SKILL.md'), 'rb') as f:
                v_hash = hashlib.md5(f.read()).hexdigest()[:8]
                versions[name] = v_hash

    with open(VERSIONS_FILE, 'w') as f:
        json.dump(versions, f, indent=2)
    print(f'Versions updated for {len(versions)} skills.')

if __name__ == '__main__':
    update_versions()
