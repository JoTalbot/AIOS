import os

SKILLS_ROOT = '/root/agents/-Octopus/skills/core'

def find_dead_skills():
    print('[HUNTER] Searching for hollow skill stubs...')
    total = 0
    dead = []
    for folder in os.listdir(SKILLS_ROOT):
        skill_path = os.path.join(SKILLS_ROOT, folder)
        code_file = os.path.join(skill_path, 'code.py')
        total += 1
        if not os.path.exists(code_file):
            dead.append(folder)
            
    print(f'[HUNTER] Found {len(dead)}/{total} skills without executable code.')
    return dead

if __name__ == '__main__':
    find_dead_skills()
