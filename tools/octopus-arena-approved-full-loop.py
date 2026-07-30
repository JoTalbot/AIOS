#!/usr/bin/env python3
"""Approved full loop for Arena/Gemini port.

Flow:
  left answer file -> validator/optional execute -> stdout pasteback dry-run/live browser

This tool never bypasses the validator. SSH/terminal execution requires exact approval phrase.
Browser pasteback requires OCTOPUS_ALLOW_BROWSER_AI_BRIDGE=1 unless --pasteback-dry-run.
"""
from __future__ import annotations
import argparse, datetime as dt, json, pathlib, subprocess, sys
ROOT=pathlib.Path('/root/agents/-Octopus')
REPORTS=ROOT/'reports'
LOOP=ROOT/'tools'/'octopus-arena-agent-loop.py'
PASTE=ROOT/'tools'/'octopus-arena-stdout-pasteback.py'
APPROVAL='РАЗРЕШАЮ ВЫПОЛНИТЬ SSH КОМАНДУ'

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--answer-file', required=True)
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--approval', default='')
    ap.add_argument('--pasteback-dry-run', action='store_true')
    ap.add_argument('--pasteback-live', action='store_true')
    ap.add_argument('--submit', action='store_true')
    args=ap.parse_args()
    run=REPORTS/('arena_approved_full_loop_'+dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ'))
    run.mkdir(parents=True, exist_ok=True)
    cmd=[str(LOOP),'--answer-file',args.answer_file]
    if args.execute:
        cmd += ['--execute','--approval',args.approval]
    proc=subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (run/'AGENT_LOOP_STDOUT.txt').write_text(proc.stdout)
    (run/'AGENT_LOOP_STDERR.txt').write_text(proc.stderr)
    paste_result=None
    if args.pasteback_dry_run or args.pasteback_live:
        pcmd=[str(PASTE),'--stdout-file',str(run/'AGENT_LOOP_STDOUT.txt')]
        if args.pasteback_dry_run:
            pcmd.append('--dry-run')
        if args.submit:
            pcmd.append('--submit')
        p=subprocess.run(pcmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (run/'PASTEBACK_STDOUT.txt').write_text(p.stdout)
        (run/'PASTEBACK_STDERR.txt').write_text(p.stderr)
        paste_result={'returncode':p.returncode,'stdout_file':str(run/'PASTEBACK_STDOUT.txt')}
    meta={'run':str(run),'agent_loop_returncode':proc.returncode,'pasteback':paste_result,'execute':args.execute,'approval_ok':args.approval==APPROVAL,'status':'ok' if proc.returncode==0 else 'blocked_or_failed'}
    (run/'RESULT.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0 if proc.returncode==0 else proc.returncode
if __name__ == '__main__':
    raise SystemExit(main())
