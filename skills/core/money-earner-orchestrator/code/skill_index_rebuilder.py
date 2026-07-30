#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/root/agents/-Octopus')
SKILLS = ROOT / 'skills'
INDEX = SKILLS / 'index.json'
CATEGORIES = ('core', 'dr', 'loader', 'marketplace', 'mcp', 'meta', 'research')


def parse_meta(skill_md: Path) -> dict:
    text = skill_md.read_text(errors='replace')
    name = skill_md.parent.name
    description = ''
    version = '1.0'
    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                if ':' not in line:
                    continue
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip(chr(34)).strip(chr(39))
                if key == 'name' and value:
                    name = value
                elif key == 'description':
                    description = value
                elif key == 'version' and value:
                    version = value
    if not description:
        match = re.search(r'(?im)^## Описание\s*\n+(.+)$', text)
        if match:
            description = match.group(1).strip()
    return {
        'name': name,
        'version': version,
        'description': description,
        'triggers': [],
        'dependencies': [],
        'llm_required': False,
        'mcp_tools': [],
    }


def build() -> dict:
    current = json.loads(INDEX.read_text()) if INDEX.exists() else {}
    current_skills = current.get('skills', {})
    skills = {}
    by_name = defaultdict(list)
    for category in CATEGORIES:
        root = SKILLS / category
        if not root.exists():
            continue
        for directory in sorted(path for path in root.iterdir() if path.is_dir()):
            skill_md = directory / 'SKILL.md'
            if not skill_md.exists():
                continue
            skill_id = f'{category}/{directory.name}'
            meta = dict(current_skills.get(skill_id) or parse_meta(skill_md))
            has_code = (directory / 'code/run.py').exists() or (directory / 'code.py').exists()
            has_tests = (directory / 'tests').exists() and any((directory / 'tests').glob('test_*.py'))
            text = skill_md.read_text(errors='replace')
            item = {
                **meta,
                'id': skill_id,
                'category': category,
                'dir_name': directory.name,
                'path': str(directory),
                'has_description': meta.get('has_description', bool(meta.get('description') or '## Описание' in text)),
                'has_algorithm': meta.get('has_algorithm', ('## Алгоритм' in text or '# Skill Marketplace Sync' in text)),
                'has_code': has_code,
                'has_tests': has_tests,
                'stub': not (has_code and has_tests),
            }
            skills[skill_id] = item
            by_name[item['name']].append(skill_id)
    real_ids = sorted(key for key, value in skills.items() if not value['stub'])
    stub_ids = sorted(key for key, value in skills.items() if value['stub'])
    duplicates = {key: sorted(value) for key, value in by_name.items() if len(value) > 1}
    categories = {category: count for category in CATEGORIES if (count := sum(1 for key in skills if key.startswith(category + '/'))) > 0}
    now = datetime.now(timezone.utc).isoformat()
    audit = {
        'total': len(skills),
        'unique_names': len(by_name),
        'real_skills': len(real_ids),
        'stubs': len(stub_ids),
        'stub_ids': stub_ids,
        'stub_names': sorted({skills[key]['name'] for key in stub_ids}),
        'real_ids': real_ids,
        'real_names': sorted({skills[key]['name'] for key in real_ids}),
        'duplicate_names': duplicates,
        'duplicate_count': len(duplicates),
        'categories': categories,
        'timestamp': now,
    }
    return {
        'version': '3.1',
        'timestamp': now,
        'audit': audit,
        'skills': dict(sorted(skills.items())),
        'skills_by_name': {key: sorted(value) for key, value in sorted(by_name.items())},
    }


def normalized(data: dict) -> dict:
    value = json.loads(json.dumps(data))
    value.pop('timestamp', None)
    value.get('audit', {}).pop('timestamp', None)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true')
    group.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    fresh = build()
    current = json.loads(INDEX.read_text()) if INDEX.exists() else {}
    changed = normalized(fresh) != normalized(current)
    result = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'mode': 'apply' if args.apply else 'check',
        'changed': changed,
        'audit': fresh['audit'],
        'index': str(INDEX),
        'applied': False,
    }
    if args.apply and changed:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        backup = INDEX.with_name(INDEX.name + '.bak.rebuild.' + stamp)
        if INDEX.exists():
            shutil.copy2(INDEX, backup)
            result['backup'] = str(backup)
        fd, temp_name = tempfile.mkstemp(prefix='index.json.', dir=str(SKILLS))
        with os.fdopen(fd, 'w') as handle:
            json.dump(fresh, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, INDEX)
        result['applied'] = True
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(1 if args.check and changed else 0)


if __name__ == '__main__':
    main()
