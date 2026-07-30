import os

SKILLS_ROOT = '/root/agents/-Octopus/skills/core'

def check_integrity():
    print('--- Octopus Skill Integrity Report ---')
    total = 0
    passed = 0
    for folder in os.listdir(SKILLS_ROOT):
        path = os.path.join(SKILLS_ROOT, folder, 'SKILL.md')
        if os.path.exists(path):
            total += 1
            with open(path, 'r') as f:
                content = f.read()
                # Check for standard sections
                if '## Описание' in content and '## Инструкции' in content:
                    passed += 1
                else:
                    print(f'[WARN] Skill {folder} is missing standard sections.')

    print(f'Summary: {passed}/{total} skills follow the standard.')

if __name__ == '__main__':
    check_integrity()
