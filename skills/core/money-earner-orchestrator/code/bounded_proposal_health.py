#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
B=Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator'); D=B/'data'
report=D/'bounded_adaptation_proposals_latest.json'
errors=[]
try:
    data=json.loads(report.read_text())
except Exception as e:
    data={}; errors.append('missing_or_invalid_report:'+type(e).__name__)
if data:
    if data.get('mode')!='bounded_proposals_only': errors.append('invalid_mode')
    if data.get('external_actions_performed') is not False: errors.append('external_actions_flag_not_false')
    proposals=data.get('proposals')
    if not isinstance(proposals,list): errors.append('proposals_not_list'); proposals=[]
    if data.get('proposal_count')!=len(proposals): errors.append('proposal_count_mismatch')
    ids=[]
    for i,p in enumerate(proposals):
        if not isinstance(p,dict): errors.append(f'proposal_{i}_not_object'); continue
        pid=p.get('id'); ids.append(pid)
        if not pid: errors.append(f'proposal_{i}_missing_id')
        if p.get('auto_apply') is not False: errors.append(f'{pid or i}_auto_apply_not_false')
    if len(ids)!=len(set(ids)): errors.append('duplicate_proposal_ids')
out={'generated_at':datetime.now(timezone.utc).isoformat(),'report':str(report),'proposal_count':data.get('proposal_count'),'errors':errors,'healthy':not errors}
(D/'bounded_proposal_health_latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
raise SystemExit(0 if out['healthy'] else 1)
