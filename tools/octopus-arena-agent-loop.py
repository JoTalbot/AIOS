#!/usr/bin/env python3
"""Controlled Arena/Gemini agent loop.

Supported safe flow:
1) post prompt to Arena manually or via browser template;
2) choose left AI answer;
3) feed answer to this script via --answer-file or stdin;
4) validator blocks dangerous commands;
5) execution requires --execute and exact approval phrase;
6) stdout is written to a pasteback file, optionally copied to clipboard if xclip/wl-copy/pbcopy exists.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, pathlib, re, shutil, subprocess, sys

ROOT = pathlib.Path('/root/agents/-Octopus')
REPORTS = ROOT / 'reports'
BRIDGE = ROOT / 'tools' / 'octopus-gemini-ssh-bridge.py'
APPROVAL = 'РАЗРЕШАЮ ВЫПОЛНИТЬ SSH КОМАНДУ'

def copy_to_clipboard(text: str) -> str:
    candidates = [
        ('xclip', ['xclip', '-selection', 'clipboard']),
        ('wl-copy', ['wl-copy']),
        ('pbcopy', ['pbcopy']),
    ]
    for name, cmd in candidates:
        if shutil.which(name):
            try:
                subprocess.run(cmd, input=text, text=True, check=True, timeout=10)
                return name
            except Exception:
                continue
    return 'unavailable'

def read_text(path: str | None) -> str:
    if path:
        return pathlib.Path(path).read_text(errors='replace')
    return sys.stdin.read()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--answer-file', help='File containing left Arena/Gemini answer')
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--approval', default='')
    ap.add_argument('--timeout', type=int, default=900)
    ap.add_argument('--copy-stdout-to-clipboard', action='store_true')
    ap.add_argument('--print-prompt', action='store_true')
    args = ap.parse_args()
    if args.print_prompt:
        print((ROOT / 'instructions' / 'GEMINI_ARENA_SYSTEM_PROMPT_RU.md').read_text())
        return 0
    text = read_text(args.answer_file)
    run = REPORTS / ('arena_agent_loop_' + dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ'))
    run.mkdir(parents=True, exist_ok=True)
    answer_file = run / 'LEFT_ANSWER_RAW.txt'
    answer_file.write_text(text)
    cmd = [str(BRIDGE), '--file', str(answer_file), '--timeout', str(args.timeout)]
    if args.execute:
        cmd.append('--execute')
        cmd += ['--approval', args.approval]
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (run / 'BRIDGE_STDOUT.txt').write_text(proc.stdout)
    (run / 'BRIDGE_STDERR.txt').write_text(proc.stderr)
    clip = 'not_requested'
    if args.copy_stdout_to_clipboard:
        clip = copy_to_clipboard(proc.stdout)
    meta = {
        'run': str(run),
        'execute': args.execute,
        'bridge_returncode': proc.returncode,
        'clipboard': clip,
        'pasteback_file': str(run / 'BRIDGE_STDOUT.txt'),
        'status': 'ok' if proc.returncode == 0 else 'blocked_or_failed',
    }
    (run / 'RESULT.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    if proc.stdout:
        print('\n--- PASTEBACK_STDOUT ---')
        print(proc.stdout, end='')
    if proc.stderr:
        print('\n--- STDERR ---', file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
    return 0 if proc.returncode == 0 else proc.returncode

if __name__ == '__main__':
    raise SystemExit(main())
