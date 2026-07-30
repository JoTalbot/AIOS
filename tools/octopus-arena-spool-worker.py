#!/usr/bin/env python3
"""Approval-gated spool worker for Arena/Gemini left-answer commands.

Queues:
  incoming/*.txt  -> validate only; result in validated or rejected
  approved/*.txt  -> validate + execute only if approved/<stem>.approval contains exact phrase
  outbox/*.stdout -> stdout pasteback material

No blind external AI execution. Dangerous commands are blocked by octopus-gemini-ssh-bridge.py.
"""
from __future__ import annotations
import argparse, datetime as dt, json, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path('/root/agents/-Octopus')
SPOOL = pathlib.Path('/var/spool/octopus-arena-agent')
BRIDGE = ROOT / 'tools' / 'octopus-gemini-ssh-bridge.py'
APPROVAL = 'РАЗРЕШАЮ ВЫПОЛНИТЬ SSH КОМАНДУ'
DIRS = ['incoming','validated','approved','outbox','rejected','logs']

def ensure_dirs() -> None:
    for d in DIRS:
        (SPOOL/d).mkdir(parents=True, exist_ok=True)

def run_bridge(path: pathlib.Path, execute: bool = False, approval: str = '') -> subprocess.CompletedProcess[str]:
    cmd = [str(BRIDGE), '--file', str(path), '--timeout', '900']
    if execute:
        cmd += ['--execute', '--approval', approval]
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1000)

def safe_name(p: pathlib.Path) -> str:
    return ''.join(ch if ch.isalnum() or ch in '._-' else '_' for ch in p.stem)[:120]

def process_incoming(limit: int) -> list[dict]:
    results=[]
    for path in sorted((SPOOL/'incoming').glob('*.txt'))[:limit]:
        name=safe_name(path)
        ts=dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        proc=run_bridge(path, execute=False)
        rec={'file':str(path),'mode':'validate','returncode':proc.returncode,'time':ts}
        if proc.returncode==0:
            dest=SPOOL/'validated'/f'{name}.{ts}.txt'
            shutil.move(str(path), dest)
            (SPOOL/'validated'/f'{name}.{ts}.validator.stdout').write_text(proc.stdout)
            (SPOOL/'validated'/f'{name}.{ts}.validator.stderr').write_text(proc.stderr)
            rec.update({'status':'validated','dest':str(dest)})
        else:
            dest=SPOOL/'rejected'/f'{name}.{ts}.txt'
            shutil.move(str(path), dest)
            (SPOOL/'rejected'/f'{name}.{ts}.validator.stdout').write_text(proc.stdout)
            (SPOOL/'rejected'/f'{name}.{ts}.validator.stderr').write_text(proc.stderr)
            rec.update({'status':'rejected','dest':str(dest)})
        results.append(rec)
    return results

def process_approved(limit: int) -> list[dict]:
    results=[]
    for path in sorted((SPOOL/'approved').glob('*.txt'))[:limit]:
        name=safe_name(path)
        approval_file=path.with_suffix('.approval')
        ts=dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        approval=approval_file.read_text(errors='replace').strip() if approval_file.exists() else ''
        if approval != APPROVAL:
            rec={'file':str(path),'mode':'execute','status':'missing_or_bad_approval','time':ts}
            (SPOOL/'rejected'/f'{name}.{ts}.approval_error.txt').write_text('missing_or_bad_approval\n')
            results.append(rec)
            continue
        proc=run_bridge(path, execute=True, approval=approval)
        rec={'file':str(path),'mode':'execute','returncode':proc.returncode,'time':ts}
        if proc.returncode==0:
            stdout_file=SPOOL/'outbox'/f'{name}.{ts}.stdout'
            stderr_file=SPOOL/'outbox'/f'{name}.{ts}.stderr'
            stdout_file.write_text(proc.stdout)
            stderr_file.write_text(proc.stderr)
            done=SPOOL/'outbox'/f'{name}.{ts}.command.txt'
            shutil.move(str(path), done)
            try: approval_file.unlink()
            except FileNotFoundError: pass
            rec.update({'status':'executed','stdout':str(stdout_file),'stderr':str(stderr_file)})
        else:
            stdout_file=SPOOL/'rejected'/f'{name}.{ts}.execute.stdout'
            stderr_file=SPOOL/'rejected'/f'{name}.{ts}.execute.stderr'
            stdout_file.write_text(proc.stdout)
            stderr_file.write_text(proc.stderr)
            dest=SPOOL/'rejected'/f'{name}.{ts}.txt'
            shutil.move(str(path), dest)
            try: approval_file.unlink()
            except FileNotFoundError: pass
            rec.update({'status':'execute_failed_or_blocked','dest':str(dest),'stdout':str(stdout_file),'stderr':str(stderr_file)})
        results.append(rec)
    return results

def write_report(records: list[dict]) -> pathlib.Path:
    ts=dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    report=SPOOL/'logs'/f'worker_{ts}.json'
    report.write_text(json.dumps({'generated_at_utc':ts,'records':records}, ensure_ascii=False, indent=2)+'\n')
    latest=SPOOL/'logs'/'LATEST.json'
    latest.write_text(report.read_text())
    return report

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--once', action='store_true')
    ap.add_argument('--limit', type=int, default=10)
    ap.add_argument('--status', action='store_true')
    args=ap.parse_args()
    ensure_dirs()
    if args.status:
        data={d:len(list((SPOOL/d).glob('*'))) for d in DIRS}
        data['spool']=str(SPOOL)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    records=[]
    records += process_incoming(args.limit)
    records += process_approved(args.limit)
    report=write_report(records)
    print(json.dumps({'status':'ok','records':len(records),'report':str(report),'spool':str(SPOOL)}, ensure_ascii=False, indent=2))
    return 0
if __name__=='__main__':
    raise SystemExit(main())
