#!/usr/bin/env python3
"""Controlled Gemini/Arena SSH bridge.

Reads AI-generated terminal command from stdin or a file, validates dangerous patterns,
and executes only with --execute plus an approval phrase. It is intentionally not a blind
browser-to-SSH autopilot.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, pathlib, re, subprocess, sys

ROOT = pathlib.Path('/root/agents/-Octopus')
REPORTS = ROOT / 'reports'
DENY = [
    r'\brm\s+-rf\s+/', r'\bmkfs\b', r'\bdd\s+if=', r'\bshred\b', r'\btruncate\b',
    r'iptables\s+-(F|X|P)\b', r'nft\s+flush\b', r'systemctl\s+restart\s+(docker|nginx|octopus|garage|cloudflared|ssh|sshd)\b',
    r'curl\b[^|\n]*\|\s*(bash|sh)', r'wget\b[^|\n]*\|\s*(bash|sh)',
    r'BEGIN (RSA |EC |OPENSSH |)?PRIVATE KEY', r'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}',
]
SENSITIVE = re.compile(r'(?i)(api[_-]?token|access[_-]?token|secret[_-]?key|password|cloudflare.*token)')
APPROVAL = 'РАЗРЕШАЮ ВЫПОЛНИТЬ SSH КОМАНДУ'

def extract_command(text: str) -> str:
    text = text.strip()
    # Prefer fenced command content, but accept raw command.
    m = re.search(r'```(?:bash|sh|shell)?\s*(.*?)```', text, re.S | re.I)
    if m:
        text = m.group(1).strip()
    return text

def validate(cmd: str) -> list[str]:
    issues = []
    if not cmd:
        issues.append('empty_command')
    if SENSITIVE.search(cmd):
        issues.append('sensitive_literal_or_assignment_detected')
    for pat in DENY:
        if re.search(pat, cmd, re.I):
            issues.append(f'deny_pattern:{pat}')
    if len(cmd) > 20000:
        issues.append('command_too_large')
    return issues

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--file')
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--approval', default='')
    ap.add_argument('--timeout', type=int, default=600)
    args = ap.parse_args()
    raw = pathlib.Path(args.file).read_text() if args.file else sys.stdin.read()
    cmd = extract_command(raw)
    issues = validate(cmd)
    run = REPORTS / ('gemini_ssh_bridge_run_' + dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ'))
    run.mkdir(parents=True, exist_ok=True)
    (run / 'COMMAND_REDACTED.txt').write_text(re.sub(r'(?i)(token|password|secret)[^\s]*', '<redacted>', cmd) + '\n')
    meta = {'run': str(run), 'execute_requested': args.execute, 'issues': issues, 'approval_ok': args.approval == APPROVAL}
    if issues:
        meta['status'] = 'blocked_by_validator'
        (run / 'RESULT.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return 4
    if not args.execute:
        meta['status'] = 'validated_dry_run'
        (run / 'RESULT.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return 0
    if args.approval != APPROVAL:
        meta['status'] = 'blocked_missing_approval_phrase'
        (run / 'RESULT.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return 3
    proc = subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=args.timeout)
    (run / 'STDOUT.txt').write_text(proc.stdout)
    (run / 'STDERR.txt').write_text(proc.stderr)
    meta.update({'status': 'executed', 'returncode': proc.returncode})
    (run / 'RESULT.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
    print(proc.stdout, end='')
    if proc.stderr:
        print('\n--- STDERR ---\n' + proc.stderr, file=sys.stderr)
    return proc.returncode

if __name__ == '__main__':
    raise SystemExit(main())
