#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime,timezone
import json, urllib.request, urllib.error
D=Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator/data')
page='https://jotalbot.github.io/octopus/services/?health='+str(int(datetime.now(timezone.utc).timestamp()))
meta='https://jotalbot.github.io/octopus/services/income-api.json'
def get(url):
 try:
  req=urllib.request.Request(url,headers={'Cache-Control':'no-cache','User-Agent':'Octopus-Storefront-Health/1.0'})
  with urllib.request.urlopen(req,timeout=20) as r:return r.status,r.read().decode('utf-8','replace')
 except urllib.error.HTTPError as e:return e.code,e.read().decode('utf-8','replace')
 except Exception as e:return 0,str(e)
pc,pb=get(page); mc,mb=get(meta)
try: m=json.loads(mb)
except Exception: m={}
api=m.get('public_base_url',''); ac,ab=get(api+'/health') if api.startswith('https://') else (0,'')
tests={'page':{'code':pc,'ok':pc==200 and 'id="lead-form"' in pb and 'Submit for review' in pb},'metadata':{'code':mc,'ok':mc==200 and m.get('ok') is True and api.startswith('https://')},'api':{'code':ac,'ok':ac==200}}
out={'generated_at':datetime.now(timezone.utc).isoformat(),'mode':'storefront_live_health','public_base_url':api,'tests':tests,'ok':all(x['ok'] for x in tests.values())}
(D/'income_storefront_health_latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(out,ensure_ascii=False)); raise SystemExit(0 if out['ok'] else 1)
