#!/usr/bin/env python3
import json, subprocess
from datetime import datetime, timezone
from pathlib import Path
B=Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator'); OUT=B/'data/timer_health_latest.json'
units=['octopus-money-autopilot.timer','octopus-skill-evolution.timer','octopus-autonomous-agent.timer','octopus-all-vectors-dev.timer']
rows=[]
for u in units:
 p=subprocess.run(['systemctl','show',u,'-p','ActiveState','-p','SubState','-p','NextElapseUSecRealtime','-p','LastTriggerUSec','--no-pager'],capture_output=True,text=True,timeout=10)
 row={'unit':u,'ok':p.returncode==0}
 for line in p.stdout.splitlines():
  if '=' in line:
   k,v=line.split('=',1); row[k]=v
 row['healthy']=row.get('ActiveState')=='active'
 rows.append(row)
out={'generated_at':datetime.now(timezone.utc).isoformat(),'timers':rows,'healthy':all(x['healthy'] for x in rows)}
OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'healthy':out['healthy'],'timers':len(rows)}))
