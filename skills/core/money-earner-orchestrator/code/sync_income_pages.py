#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import base64, json, os, subprocess
B=Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator')
url=(B/'data/income_mvp_public_url.txt').read_text().strip()
if not url.startswith('https://'): raise SystemExit('invalid public url')
env={**os.environ,'GH_TOKEN':Path('/root/.gh_token').read_text().strip()}
repo='JoTalbot/octopus'
def gh_json(args):
 p=subprocess.run(['gh','api',*args],env=env,capture_output=True,text=True,check=True)
 return json.loads(p.stdout) if p.stdout.strip() else {}
def put(path,content,message):
 try: cur=gh_json([f'repos/{repo}/contents/{path}']); sha=cur.get('sha'); old=base64.b64decode(cur.get('content','')).decode()
 except Exception: sha=None; old=''
 if old==content: return False
 cmd=['gh','api','--method','PUT',f'repos/{repo}/contents/{path}','-f',f'message={message}','-f',f'content={base64.b64encode(content.encode()).decode()}','-f','branch=main']
 if sha: cmd += ['-f',f'sha={sha}']
 subprocess.run(cmd,env=env,check=True,capture_output=True,text=True)
 return True
try:
 current=gh_json([f'repos/{repo}/contents/docs/services/income-api.json'])
 current_meta=json.loads(base64.b64decode(current.get('content','')).decode())
except Exception:
 current_meta={}
if current_meta.get('public_base_url')==url:
 meta=json.dumps(current_meta,indent=2)+'\n'
else:
 meta=json.dumps({'generated_at':datetime.now(timezone.utc).isoformat(),'public_base_url':url,'ok':True,'temporary_endpoint':True},indent=2)+'\n'
readme='# Octopus SRE Services\n\nStable storefront: https://jotalbot.github.io/octopus/services/\n\nThe live API endpoint is read from `income-api.json` and changes only when the tunnel URL changes.\n'
changed_meta=put('docs/services/income-api.json',meta,'docs: sync services endpoint')
changed_readme=put('docs/services/README.md',readme,'docs: fix services README')
print(json.dumps({'changed':changed_meta or changed_readme,'url_changed':changed_meta,'readme_fixed':changed_readme,'public_base_url':url}))
