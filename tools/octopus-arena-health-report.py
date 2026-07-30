#!/usr/bin/env python3
"""Arena/Gemini port health report.

Read-only status for controlled browser/SSH/spool/pasteback integration.
Never executes AI commands.
"""
from __future__ import annotations
import datetime as dt, json, pathlib, subprocess, os
ROOT=pathlib.Path('/root/agents/-Octopus')
SPOOL=pathlib.Path('/var/spool/octopus-arena-agent')
TOOLS={
 'prompt': ROOT/'instructions/GEMINI_ARENA_SYSTEM_PROMPT_RU.md',
 'workflow_agent_loop': ROOT/'instructions/ARENA_AGENT_LOOP_WORKFLOW_RU.md',
 'workflow_browser': ROOT/'instructions/ARENA_BROWSER_AUTOMATION_WORKFLOW_RU.md',
 'workflow_pasteback': ROOT/'instructions/ARENA_STDOUT_PASTEBACK_WORKFLOW_RU.md',
 'workflow_spool': ROOT/'instructions/ARENA_SPOOL_QUEUE_WORKFLOW_RU.md',
 'policy_hygiene': ROOT/'instructions/ARENA_SPOOL_HYGIENE_POLICY_RU.md',
 'ssh_bridge': ROOT/'tools/octopus-gemini-ssh-bridge.py',
 'agent_loop': ROOT/'tools/octopus-arena-agent-loop.py',
 'browser_controller': ROOT/'tools/octopus-arena-browser-controller.py',
 'live_smoke': ROOT/'tools/octopus-arena-live-smoke.py',
 'pasteback': ROOT/'tools/octopus-arena-stdout-pasteback.py',
 'full_loop': ROOT/'tools/octopus-arena-approved-full-loop.py',
 'spool_worker': ROOT/'tools/octopus-arena-spool-worker.py',
 'spool_hygiene': ROOT/'tools/octopus-arena-spool-hygiene.py',
}

def cmd(args):
    try:
        p=subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        return {'rc':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()[:500]}
    except Exception as e:
        return {'rc':999,'stdout':'','stderr':type(e).__name__}

def count_files(path: pathlib.Path):
    return sum(1 for p in path.rglob('*') if p.is_file()) if path.exists() else 0

def size_bytes(path: pathlib.Path):
    total=0
    if path.exists():
        for p in path.rglob('*'):
            try:
                if p.is_file(): total += p.stat().st_size
            except FileNotFoundError:
                pass
    return total

def service(name: str):
    return {'enabled':cmd(['systemctl','is-enabled',name])['stdout'], 'active':cmd(['systemctl','is-active',name])['stdout']}

def main():
    spool_dirs={d:{'files':count_files(SPOOL/d),'bytes':size_bytes(SPOOL/d)} for d in ['incoming','validated','approved','outbox','rejected','logs','archive']}
    tool_status={k:{'exists':v.exists(),'executable':os.access(v, os.X_OK) if v.exists() else False,'path':str(v)} for k,v in TOOLS.items()}
    timers={
      'spool_worker_timer': service('octopus-arena-spool-worker.timer'),
      'spool_hygiene_timer': service('octopus-arena-spool-hygiene.timer'),
      'p0_p1_firewall_service': service('octopus-p0-firewall.service'),
    }
    prod_guard=cmd(['/usr/local/sbin/octopus-production-guard-report','/var/tmp/octopus-production-guard-report.out'])
    disk=cmd(['bash','-lc',"df -P / | awk 'NR==2 {gsub(\"%\",\"\",$5); print $5}'"])
    try: disk_percent=int(disk['stdout'].splitlines()[-1])
    except Exception: disk_percent=None
    ready=all(x['exists'] for x in tool_status.values()) and timers['spool_worker_timer']['active']=='active' and timers['spool_hygiene_timer']['active']=='active'
    status='ready' if ready else 'degraded'
    data={
      'generated_at_utc':dt.datetime.utcnow().replace(microsecond=0).isoformat()+'Z',
      'status':status,
      'disk_percent':disk_percent,
      'disk_status':'warning_ge_90' if disk_percent is not None and disk_percent>=90 else 'ok',
      'blind_external_ai_exec':'disabled',
      'ssh_execute_gate':'validator_plus_exact_approval',
      'browser_live_gate':'OCTOPUS_ALLOW_BROWSER_AI_BRIDGE=1',
      'spool':{'root':str(SPOOL),'dirs':spool_dirs,'total_files':count_files(SPOOL),'total_bytes':size_bytes(SPOOL)},
      'tools':tool_status,
      'timers':timers,
      'production_guard_refresh_rc':prod_guard['rc'],
    }
    print(json.dumps(data, ensure_ascii=False, indent=2))
if __name__=='__main__':
    main()
