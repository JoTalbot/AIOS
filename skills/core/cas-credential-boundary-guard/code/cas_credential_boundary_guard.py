import json, os, re, sys
from pathlib import Path
from datetime import datetime, timezone

PATTERNS = [
    re.compile(r'(?:password|passwd|pwd|secret|token|api_key|apikey|bearer|auth_token)\s*[=:]\s*["\']?[A-Za-z0-9_\-+/=!@#$%^&*]{8,}', re.IGNORECASE),
    re.compile(r'(?:AIzaSy[A-Za-z0-9_\-]{33})'),
    re.compile(r'(?:ghp_[A-Za-z0-9]{36})'),
    re.compile(r'(?:sk-[A-Za-z0-9]{48})'),
    re.compile(r'(?:xox[bsp]-[A-Za-z0-9\-]{10,})'),
]

ALLOWED = ['/etc/octopus/', '/root/.env', str(Path.home() / '.env')]

# Тестовые/placeholder-значения, которые НЕ являются реальными секретами (Фаза 3: снижение шума)
FALSE_POSITIVE_VALUES = {
    'test-secret', 'my-secret', 'correct', 'example', 'placeholder', 'changeit',
    'changeme', 'dummy', 'fake', 'dummy-key', 'your-key-from', 'xxxx', 'your_',
    'test', 'sample', 'mock', 'demo', 'secret123', 'password123',
}

def is_allowed(filepath):
    p = str(filepath)
    return any(p.startswith(a) for a in ALLOWED)

def is_false_positive(text):
    """True, если совпадение — это тестовая заглушка, а не реальный секрет."""
    low = text.lower()
    return any(fpv in low for fpv in FALSE_POSITIVE_VALUES)

def scan_path(base_path, max_files=500):
    findings = []
    for root, dirs, files in os.walk(base_path):
        if any(x in root for x in ['node_modules', '__pycache__', '.git']):
            continue
        for f in files:
            fp = Path(root) / f
            if fp.suffix.lower() not in {'.py', '.js', '.ts', '.json', '.yaml', '.yml', '.env', '.sh'}:
                continue
            if is_allowed(fp):
                continue
            try:
                text = fp.read_text(errors='ignore')
                hits = [p.pattern for p in PATTERNS if p.search(text)]
                if hits and not is_false_positive(text):
                    findings.append({'file': str(fp), 'patterns': hits})
            except Exception:
                pass
    return findings[:max_files]

def main():
    base = Path('/root/agents/-Octopus')
    findings = scan_path(base)
    print(json.dumps({'findings': findings, 'count': len(findings)}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
