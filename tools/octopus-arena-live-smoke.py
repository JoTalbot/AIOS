#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, subprocess, sys, datetime as dt
ROOT=pathlib.Path('/root/agents/-Octopus')
RUN_BASE=ROOT/'reports'
OUT=pathlib.Path('/var/tmp/octopus-arena-left-answer.txt')
CTRL=ROOT/'tools'/'octopus-arena-browser-controller.py'
LOOP=ROOT/'tools'/'octopus-arena-agent-loop.py'

def run(cmd, env=None, timeout=90):
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=timeout)

def main():
    run_dir=RUN_BASE/('arena_live_smoke_inner_'+dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ'))
    run_dir.mkdir(parents=True, exist_ok=True)
    env=os.environ.copy(); env['OCTOPUS_ALLOW_BROWSER_AI_BRIDGE']='1'
    meta={'run':str(run_dir),'out':str(OUT),'steps':{},'ssh_execute':'not_performed'}
    # Dry-run first.
    p=run([str(CTRL),'--dry-run'], timeout=30)
    (run_dir/'01_dryrun.stdout').write_text(p.stdout); (run_dir/'01_dryrun.stderr').write_text(p.stderr)
    meta['steps']['dry_run']={'rc':p.returncode}
    # Try headless post prompt. Some sites may block selector/login; capture only status, no secrets.
    p=run([str(CTRL),'--post-prompt','--headless'], env=env, timeout=90)
    (run_dir/'02_post_prompt.stdout').write_text(p.stdout); (run_dir/'02_post_prompt.stderr').write_text(p.stderr)
    meta['steps']['post_prompt']={'rc':p.returncode,'stdout_head':p.stdout[:500],'stderr_head':p.stderr[:500]}
    # Try extract + validate headless. This may return empty if no generated answer/session/login.
    p=run([str(CTRL),'--extract-left-answer','--validate-left-answer','--headless','--wait-seconds','8','--out',str(OUT)], env=env, timeout=120)
    (run_dir/'03_extract_validate.stdout').write_text(p.stdout); (run_dir/'03_extract_validate.stderr').write_text(p.stderr)
    meta['steps']['extract_validate']={'rc':p.returncode,'stdout_head':p.stdout[:800],'stderr_head':p.stderr[:500]}
    meta['left_answer_exists']=OUT.exists()
    meta['left_answer_size']=OUT.stat().st_size if OUT.exists() else 0
    if OUT.exists():
        # Always run standalone validator dry-run; never execute.
        p=run([str(LOOP),'--answer-file',str(OUT)], timeout=90)
        (run_dir/'04_loop_validator.stdout').write_text(p.stdout); (run_dir/'04_loop_validator.stderr').write_text(p.stderr)
        meta['steps']['loop_validator']={'rc':p.returncode,'stdout_head':p.stdout[:800],'stderr_head':p.stderr[:500]}
    meta['status']='live_smoke_completed_guarded'
    (run_dir/'RESULT.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(meta,ensure_ascii=False,indent=2))
    return 0
if __name__=='__main__':
    raise SystemExit(main())
