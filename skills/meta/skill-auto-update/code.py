import subprocess
import os
import shutil
import hashlib

SKILLS_ROOT = '/root/agents/-Octopus/skills'
ARCHIVE_ROOT = '/root/agents/-Octopus/archive/skills'
INDEX_PATH = '/root/agents/-Octopus/skills/marketplace/index.json'

def backup_skill(root_path):
    os.makedirs(ARCHIVE_ROOT, exist_ok=True)
    skill_md = os.path.join(root_path, 'SKILL.md')
    if os.path.exists(skill_md):
        with open(skill_md, 'rb') as f:
            v_hash = hashlib.md5(f.read()).hexdigest()[:8]
        name = os.path.basename(root_path)
        archive_name = f"{name}_{v_hash}.md"
        dest = os.path.join(ARCHIVE_ROOT, archive_name)
        if not os.path.exists(dest):
            shutil.copy2(skill_md, dest)
            print(f"Backed up: {archive_name}")

def update_index():
    print('Updating skills index and performing backups...')
    index = {'skills': []}
    for root, dirs, files in os.walk(SKILLS_ROOT):
        if 'SKILL.md' in files:
            backup_skill(root)
            rel_path = os.path.relpath(root, SKILLS_ROOT)
            name = os.path.basename(root)
            index['skills'].append({
                'name': name,
                'path': rel_path,
                'category': rel_path.split('/')[0]
            })
    with open(INDEX_PATH, 'w') as f:
        json.dump(index, f, indent=2)

if __name__ == '__main__':
    import json
    update_index()
