#!/usr/bin/env python3
from __future__ import annotations
import json, os, signal, time
from datetime import datetime, timezone
from pathlib import Path
B=Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator')
OUT=B/'data/bounded_process_guard_latest.json'
MAX_AGE=240
TARGETS=(
 'code/octopus_money_autopilot.py',
 'code/playwright_faucet_claimer.py',
 'code/opportunity_aggregate_runner.py',
 'code/roadmap_audit_batch.py',
)
def ancestors(pid:int)->set[int]:
 out=set()
 while pid>1 and pid not in out:
  out.add(pid)
  try:
   for line in Path(f'/proc/{pid}/status').read_text().splitlines():
    if line.startswith('PPid:'):
     pid=int(line.split()[1]); break
   else: break
  except Exception: break
 return out
def uptime_seconds()->float:
 return float(Path('/proc/uptime').read_text().split()[0])
def proc_age(pid:int,up:float)->float:
 stat=Path(f'/proc/{pid}/stat').read_text().split()
 ticks=os.sysconf(os.sysconf_names['SC_CLK_TCK'])
 return max(0.0,up-(int(stat[21])/ticks))
def cmdline(pid:int)->str:
 return Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode('utf-8','replace').strip()
def main():
 mine=ancestors(os.getpid()); up=uptime_seconds(); active=[]; terminated=[]; errors=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit(): continue
  pid=int(p.name)
  if pid in mine: continue
  try:
   cmd=cmdline(pid)
   if not any(t in cmd for t in TARGETS): continue
   age=round(proc_age(pid,up),1)
   row={'pid':pid,'age_seconds':age,'cmd':cmd[:500]}
   active.append(row)
   if age>MAX_AGE:
    os.kill(pid,signal.SIGTERM); row['signal']='TERM'; terminated.append(row)
  except (FileNotFoundError,ProcessLookupError,PermissionError): pass
  except Exception as e: errors.append({'pid':pid,'error':str(e)[:160]})
 if terminated:
  time.sleep(2)
  for row in terminated:
   try:
    os.kill(row['pid'],0)
    os.kill(row['pid'],signal.SIGKILL); row['signal']='KILL'
   except (ProcessLookupError,FileNotFoundError): row['exited']=True
   except Exception as e: errors.append({'pid':row['pid'],'error':str(e)[:160]})
 report={'generated_at':datetime.now(timezone.utc).isoformat(),'max_age_seconds':MAX_AGE,'active':active,'terminated':terminated,'errors':errors}
 OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'active':len(active),'terminated':len(terminated),'errors':len(errors)}))
if __name__=='__main__': main()
