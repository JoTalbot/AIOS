#!/usr/bin/env python3
import json
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
B=Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator'); D=B/'data'
def load(n,d):
 try:return json.loads((D/n).read_text())
 except Exception:return d
f=load('faucet_ledger.json',{'runs':[]}); b=load('daily_captcha_budget.json',{}); roi=load('source_roi_gate_latest.json',{})
stats=defaultdict(lambda:{'attempts':0,'successes':0,'http_5xx':0,'confirmed_income':0.0,'cost_usd':0.0})
for r in f.get('runs',[]):
 src=str(r.get('faucet') or r.get('mode') or r.get('method') or 'unknown')
 s=stats[src]; s['attempts']+=1
 if r.get('success') or r.get('claims_success',0): s['successes']+=1
 code=int(r.get('http_status') or r.get('status_code') or 0)
 if code>=500 or 'HTTP 500' in str(r.get('details','')): s['http_5xx']+=1
 if r.get('success') or r.get('claims_success',0): s['confirmed_income']+=float(r.get('amount_sats') or r.get('total_sats_claimed') or 0)
# Attribute known captcha spend proportionally only for ranking; authoritative budget stays separate.
total_attempts=sum(x['attempts'] for x in stats.values()) or 1
spent=float(b.get('spent_usd',0) or 0)
for src,s in stats.items():
 s['cost_usd']=round(spent*s['attempts']/total_attempts,6)
 s['roi_proxy']=round(s['confirmed_income']-s['cost_usd'],6)
 if s['http_5xx']>=5: state='COOLDOWN_24H'
 elif s['attempts']>=3 and s['successes']==0: state='BLOCKED_NEGATIVE_ROI'
 elif s['successes']>0: state='ACTIVE'
 else: state='PROBE'
 s['state']=state
out={'generated_at':datetime.now(timezone.utc).isoformat(),'policy':{'three_failed_paid_attempts_block':True,'five_http_5xx_cooldown_hours':24},'sources':dict(sorted(stats.items(),key=lambda kv:(kv[1]['state']!='ACTIVE',-kv[1]['roi_proxy'])))}
(D/'source_control_plane_latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'sources':len(stats),'active':sum(1 for x in stats.values() if x['state']=='ACTIVE'),'blocked':sum(1 for x in stats.values() if x['state'].startswith('BLOCKED')),'cooldown':sum(1 for x in stats.values() if x['state'].startswith('COOLDOWN'))}))
