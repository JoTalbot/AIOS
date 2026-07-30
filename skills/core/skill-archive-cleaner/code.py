import os
from collections import defaultdict

ARCHIVE_ROOT = '/root/agents/-Octopus/archive/skills'
KEEP_COUNT = 5

def cleanup():
    if not os.path.exists(ARCHIVE_ROOT): return
    files = os.listdir(ARCHIVE_ROOT)
    skill_versions = defaultdict(list)
    
    for f in files:
        if '_' in f and f.endswith('.md'):
            base_name = f.rsplit('_', 1)[0]
            mtime = os.path.getmtime(os.path.join(ARCHIVE_ROOT, f))
            skill_versions[base_name].append((f, mtime))
            
    for name, versions in skill_versions.items():
        if len(versions) > KEEP_COUNT:
            # Sort by mtime ascending (oldest first)
            versions.sort(key=lambda x: x[1])
            to_delete = versions[:-KEEP_COUNT]
            for f_del, _ in to_delete:
                print(f'[CLEANUP] Removing old version: {f_del}')
                os.remove(os.path.join(ARCHIVE_ROOT, f_del))

if __name__ == '__main__':
    cleanup()
