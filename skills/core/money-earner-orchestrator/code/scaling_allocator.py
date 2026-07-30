#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
B=Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator'); D=B/'data'
def load(n,d):
 try:return json.loads((D/n).read_text())
 except Exception:return d
cp=load('source_control_plane_latest.json',{'sources':{}})
elig=[(k,v) for k,v in cp.get('sources',{}).items() if v.get('state')=='ACTIVE' and v.get('confirmed_income',0)>0]
elig.sort(key=lambda kv:kv[1].get('roi_proxy',0),reverse=True)
alloc={}
if elig:
 alloc[elig[0][0]]=50
 if len(elig)>1: alloc[elig[1][0]]=30
out={'generated_at':datetime.now(timezone.utc).isoformat(),'eligible_sources':[k for k,_ in elig],'allocation_percent':alloc,'canary_percent':15 if elig else 0,'research_percent':5,'scaling_enabled':bool(elig),'reason':'confirmed_positive_sources_required'}
(D/'scaling_allocator_latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out))
