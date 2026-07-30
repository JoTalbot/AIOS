#!/usr/bin/env python3
import json, urllib.request
from datetime import datetime, timezone
from pathlib import Path

R=Path('/root/agents/-Octopus')
B=R/'skills/core/money-earner-orchestrator'
D=B/'data'

def get(url):
    try:
        with urllib.request.urlopen(url,timeout=8) as r:
            return r.status,json.loads(r.read().decode())
    except Exception as e:
        return 0,{'error':type(e).__name__}

checks={}
for name,path in [('health','/health'),('offers','/offers')]:
    code,body=get('http://127.0.0.1:8125'+path)
    checks[name]={'ok':code==200 and body.get('ok') is True,'code':code}
try:
    catalog=json.loads((R/'config/service_catalog.json').read_text())
except Exception:
    catalog={'services':[]}
for item in catalog.get('services',[]):
    sid=item.get('id','')
    code,body=get('http://127.0.0.1:8125/offers/'+sid)
    service=body.get('service',{}) if isinstance(body,dict) else {}
    checks['offer_'+sid]={'ok':code==200 and body.get('ok') is True and service.get('service_id')==sid,'code':code}
try:
    sales=json.loads((D/'income_sales_status_latest.json').read_text())
except Exception:
    sales={}
checks['canary_kpi']={'ok':sales.get('canaries_excluded_from_kpi') is True and sales.get('commercial_total',0)>=0,'commercial_total':sales.get('commercial_total'),'canary_total':sales.get('canary_total')}
out={'generated_at':datetime.now(timezone.utc).isoformat(),'catalog_services':len(catalog.get('services',[])),'checks':checks,'ok':all(x.get('ok') for x in checks.values())}
(D/'income_bounded_health_latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
raise SystemExit(0 if out['ok'] else 1)
