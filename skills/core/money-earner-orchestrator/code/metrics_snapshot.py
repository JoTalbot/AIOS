#!/usr/bin/env python3
import json, os
from datetime import datetime, timezone
from pathlib import Path
B=Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator'); D=B/'data'; OUT=D/'metrics_snapshot_latest.json'
def load(n,d):
 try:return json.loads((D/n).read_text())
 except Exception:return d
st=os.statvfs('/')
disk_used=100*(1-(st.f_bavail/st.f_blocks)) if st.f_blocks else 0
mem={}
for line in Path('/proc/meminfo').read_text().splitlines():
 k,v=line.split(':',1); mem[k]=int(v.strip().split()[0])
ram_used=100*(1-(mem.get('MemAvailable',0)/mem.get('MemTotal',1)))
a=load('autopilot_latest.json',{}); r=load('roadmap_audit_latest.json',{}); o=load('opportunity_aggregate_latest.json',{}); b=load('daily_captcha_budget.json',{}); e=load('earnings_ledger.json',{})
out={'generated_at':datetime.now(timezone.utc).isoformat(),'disk_used_percent':round(disk_used,2),'ram_used_percent':round(ram_used,2),'autopilot_ok':a.get('ok'),'live_verified_bounties':o.get('live_verified_total',0),'captcha_spent_usd':b.get('spent_usd',0),'paper_realized_pnl_usd':e.get('paper',{}).get('realized_pnl_usd',0),'audit_errors':len(r.get('errors',[]))}
OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(out,ensure_ascii=False))
