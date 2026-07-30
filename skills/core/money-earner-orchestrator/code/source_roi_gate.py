#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
B=Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator'); D=B/'data'
def load(path,d):
 try:return json.loads(Path(path).read_text())
 except Exception:return d
b=load(D/'daily_captcha_budget.json',{}); f=load(D/'faucet_ledger.json',{'runs':[]}); cfg=load(B/'config/faucet_config.json',{})
spent=float(b.get('spent_usd',0) or 0); confirmed_sats=0.0; attempts={}; success={}
for r in f.get('runs',[]):
 src=r.get('faucet') or r.get('mode') or r.get('method') or 'unknown'; attempts[src]=attempts.get(src,0)+1
 if r.get('success') or r.get('claims_success',0): success[src]=success.get(src,0)+1
 confirmed_sats+=float(r.get('amount_sats') or r.get('total_sats_claimed') or 0) if (r.get('success') or r.get('claims_success',0)) else 0
recommendation='block_paid_captcha' if spent>0 and confirmed_sats<=0 else 'continue_bounded'
effective='enabled_by_user_override' if cfg.get('captcha',{}).get('auto_paid_enabled',False) else 'blocked'
sources={k:{'attempts':v,'successes':success.get(k,0),'state':'BLOCKED_NEGATIVE_ROI' if v>=3 and success.get(k,0)==0 else 'PROBE'} for k,v in attempts.items()}
out={'generated_at':datetime.now(timezone.utc).isoformat(),'confirmed_sats':confirmed_sats,'captcha_spent_usd':spent,'roi_recommendation':recommendation,'effective_policy':effective,'sources':sources,'auto_write_config':False}
(D/'source_roi_gate_latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(out,ensure_ascii=False))
