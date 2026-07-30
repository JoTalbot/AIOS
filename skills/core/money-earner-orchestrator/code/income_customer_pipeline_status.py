#!/usr/bin/env python3
import json
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/agents/-Octopus'); B=R/'skills/core/money-earner-orchestrator'; D=B/'data'; CFG=R/'config'
def load(p,d):
 try:return json.loads(Path(p).read_text())
 except Exception:return d
q=load(D/'income_customer_requests.json',{'requests':[]}); k=load(CFG/'income_mvp_api_keys.json',{'keys':[]}); e=load(D/'income_mvp_public_endpoint_latest.json',{})
summary={'received':len(q.get('requests',[])),'pending_payment':sum(x.get('payment_status')=='pending' for x in q.get('requests',[])),'issued':sum(x.get('status')=='issued' for x in q.get('requests',[])),'active_customer_keys':sum(x.get('enabled') and str(x.get('name','')).startswith('customer-') for x in k.get('keys',[]))}
out={'generated_at':datetime.now(timezone.utc).isoformat(),'public_endpoint_ok':e.get('ok',False),'summary':summary}
(D/'income_customer_pipeline_latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(out,ensure_ascii=False))
