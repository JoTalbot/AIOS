#!/usr/bin/env python3
"""Octopus Arena/Gemini spool hygiene.

Owns only /var/spool/octopus-arena-agent. It archives/removes old worker artifacts
under conservative age/count/size caps. It never touches project reports outside
spool and never executes AI commands.
"""
from __future__ import annotations
import argparse, datetime as dt, gzip, json, os, pathlib, shutil, tarfile, time

SPOOL = pathlib.Path('/var/spool/octopus-arena-agent')
SUBDIRS = ['incoming','validated','approved','outbox','rejected','logs','archive']

def ensure_dirs():
    for d in SUBDIRS:
        (SPOOL/d).mkdir(parents=True, exist_ok=True)

def size_bytes(path: pathlib.Path) -> int:
    total = 0
    if path.exists():
        for p in path.rglob('*'):
            try:
                if p.is_file():
                    total += p.stat().st_size
            except FileNotFoundError:
                pass
    return total

def count_files(path: pathlib.Path) -> int:
    return sum(1 for p in path.rglob('*') if p.is_file()) if path.exists() else 0

def old_files(subdir: str, older_hours: int):
    cutoff = time.time() - older_hours * 3600
    base = SPOOL / subdir
    if not base.exists():
        return []
    return sorted([p for p in base.rglob('*') if p.is_file() and p.stat().st_mtime < cutoff], key=lambda p: p.stat().st_mtime)

def newest_limit_files(subdir: str, keep_count: int):
    base = SPOOL / subdir
    files = sorted([p for p in base.rglob('*') if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)
    return files[keep_count:]

def archive_files(files, label: str, dry_run: bool):
    if not files:
        return None, []
    ts = dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    archive = SPOOL / 'archive' / f'{label}_{ts}.tar.gz'
    removed=[]
    if dry_run:
        return str(archive), [str(p) for p in files]
    with tarfile.open(archive, 'w:gz') as tar:
        for p in files:
            if p.exists() and p.is_file():
                tar.add(p, arcname=str(p.relative_to(SPOOL)))
    for p in files:
        try:
            p.unlink()
            removed.append(str(p))
        except FileNotFoundError:
            pass
    return str(archive), removed

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--validated-hours', type=int, default=24)
    ap.add_argument('--outbox-hours', type=int, default=48)
    ap.add_argument('--rejected-hours', type=int, default=24)
    ap.add_argument('--logs-keep', type=int, default=200)
    ap.add_argument('--max-mb', type=int, default=100)
    args=ap.parse_args()
    ensure_dirs()
    dry=not args.apply
    before={'bytes': size_bytes(SPOOL), 'files': count_files(SPOOL)}
    candidates=[]
    for sub,hours in [('validated',args.validated_hours),('outbox',args.outbox_hours),('rejected',args.rejected_hours)]:
        candidates.extend(old_files(sub, hours))
    candidates.extend(newest_limit_files('logs', args.logs_keep))
    # If over size cap, prune oldest non-incoming/non-approved artifacts until below target estimate.
    max_bytes=args.max_mb*1024*1024
    if before['bytes'] > max_bytes:
        extra=[]
        for sub in ['validated','outbox','rejected','logs']:
            extra.extend([p for p in (SPOOL/sub).rglob('*') if p.is_file()])
        extra=sorted(set(extra), key=lambda p: p.stat().st_mtime)
        estimate=before['bytes']
        selected=set(candidates)
        for p in extra:
            if estimate <= max_bytes:
                break
            selected.add(p)
            try: estimate -= p.stat().st_size
            except FileNotFoundError: pass
        candidates=list(selected)
    archive, affected = archive_files(sorted(set(candidates)), 'spool_hygiene', dry)
    after={'bytes': size_bytes(SPOOL), 'files': count_files(SPOOL)}
    status='dry_run_success' if dry else 'applied_success'
    result={'generated_at_utc':dt.datetime.utcnow().replace(microsecond=0).isoformat()+'Z','status':status,'dry_run':dry,'spool':str(SPOOL),'before':before,'after':after,'candidate_count':len(set(candidates)),'archive':archive,'affected_count':len(affected),'max_mb':args.max_mb,'protected_dirs':['incoming','approved'],'note':'incoming and approved are never pruned by hygiene'}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
