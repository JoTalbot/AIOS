#!/usr/bin/env python3
import json,re,urllib.request,urllib.error
from datetime import datetime,timezone
from pathlib import Path
B=Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator'); D=B/'data'; LOG=Path('/var/log/octopus-income-serveo-tunnel.log')
urls=re.findall(r'https://[A-Za-z0-9.-]+\.serveousercontent\.com',LOG.read_text(errors='ignore') if LOG.exists() else '')
url=urls[-1] if urls else ''
def check(path,expected):
 if not url:return {'code':'000','expected':str(expected),'ok':False}
 try:
  req=urllib.request.Request(url+path,method='GET'); r=urllib.request.urlopen(req,timeout=20); code=r.status
 except urllib.error.HTTPError as e: code=e.code
 except Exception: code=0
 return {'code':str(code),'expected':str(expected),'ok':code==expected}
results={'health':check('/health',200),'pricing':check('/pricing',200)}
out={'generated_at':datetime.now(timezone.utc).isoformat(),'public_base_url':url,'provider':'serveo','tls':url.startswith('https://'),'persistent_hostname':False,'tests':results,'ok':bool(url) and all(x['ok'] for x in results.values())}
(D/'income_mvp_public_endpoint_latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
if url:(D/'income_mvp_public_url.txt').write_text(url+'\n')
print(json.dumps(out,ensure_ascii=False)); raise SystemExit(0 if out['ok'] else 1)
