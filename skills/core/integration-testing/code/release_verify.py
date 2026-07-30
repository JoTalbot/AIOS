#!/usr/bin/env python3
"""Bounded release verification for the current Octopus security/reliability waves."""
from __future__ import annotations
import argparse, hashlib, json, re, secrets, subprocess, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROJECT=Path('/mnt/agents/-Octopus')
SOURCES=[
 PROJECT/'autopilot/server.py',
 PROJECT/'skills/mcp/skills_mcp_server.py',
 PROJECT/'skills/core/graphrag-exact-citations/code/api.py',
 PROJECT/'skills/core/cas-credential-boundary-guard/code/run.py',
 PROJECT/'skills/core/autopilot-runtime-durability-guard/code/run.py',
 PROJECT/'skills/core/orphan-session-drift-guard/code/run.py',
]
UNITS=[
 'octopus-autopilot-api.service','octopus-autopilot-runtime-guard.timer',
 'octopus-orphan-session-drift-guard.timer','octopus-cas-api.service',
 'octopus-cas-credential-guard.timer','octopus-skills-mcp-server.service',
 'octopus-graphrag-api.service','cloudflared.service','nginx.service',
]
VERIFY_FILES=[
 '/etc/systemd/system/octopus-autopilot-api.service',
 '/etc/systemd/system/octopus-autopilot-runtime-guard.service',
 '/etc/systemd/system/octopus-autopilot-runtime-guard.timer',
 '/etc/systemd/system/octopus-orphan-session-drift-guard.service',
 '/etc/systemd/system/octopus-orphan-session-drift-guard.timer',
 '/etc/systemd/system/octopus-cas-credential-guard.service',
 '/etc/systemd/system/octopus-cas-credential-guard.timer',
]

def run(cmd,timeout=30): return subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def http(url,token=None,method='GET',data=None):
 headers={'Authorization':'Bearer '+token} if token else {}
 if data is not None: headers['Content-Type']='application/json'
 req=urllib.request.Request(url,headers=headers,method=method,data=data)
 try:
  with urllib.request.urlopen(req,timeout=15) as r: r.read(256); return r.status
 except urllib.error.HTTPError as e:return e.code

def curl_http(url):
 p=subprocess.run(['curl','-sS','-o','/dev/null','-w','%{http_code}','--max-time','15',url],capture_output=True,text=True,timeout=20)
 return int(p.stdout) if p.returncode==0 and p.stdout.isdigit() else 0

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path); ap.add_argument('--json',action='store_true'); a=ap.parse_args()
 checks={}; warnings=[]; evidence={}
 existing=[p for p in SOURCES if p.is_file()]
 checks['all_sources_exist']=len(existing)==len(SOURCES)
 checks['python_compile']=run(['python3','-m','py_compile',*[str(p) for p in existing]],60).returncode==0
 evidence['source_sha256']={str(p):sha(p) for p in existing}
 checks['systemd_verify']=run(['systemd-analyze','verify',*VERIFY_FILES],60).returncode==0
 states={}
 for unit in UNITS:
  active=run(['systemctl','is-active',unit]).stdout.strip()
  nr=run(['systemctl','show',unit,'-p','NRestarts','--value']).stdout.strip() or '0'
  states[unit]={'active':active,'nrestarts':int(nr)}
 checks['units_active']=all(v['active']=='active' for v in states.values())
 checks['nrestarts_zero']=all(v['nrestarts']==0 for v in states.values())
 evidence['units']=states
 failed=run(['systemctl','list-units','--type=service','--state=failed','--no-legend','--no-pager']).stdout.splitlines()
 evidence['octopus_failed_count']=sum('octopus' in x.lower() for x in failed)
 checks['no_octopus_failed']=evidence['octopus_failed_count']==0
 checks['nginx_config_valid']=run(['nginx','-t']).returncode==0
 enabled=Path('/etc/nginx/sites-enabled/octopus-api').read_text(); available=Path('/etc/nginx/sites-available/octopus-api').read_text()
 cas_route='location /cas/ { proxy_pass http://127.0.0.1:9540/cas/; }'
 checks['active_nginx_cas_route']=cas_route in enabled
 checks['available_nginx_cas_route']=cas_route in available
 evidence['nginx_files_equal']=enabled==available
 if enabled!=available: warnings.append('sites-enabled/octopus-api differs from sites-available; active CAS route matches but full config drift remains')
 for f,key,count in [('/run/octopus/cas_credential_guard.json','cas_guard',21),('/run/octopus/autopilot_runtime_guard.json','autopilot_guard',12),('/run/octopus/orphan_session_guard.json','orphan_guard',None)]:
  p=json.load(open(f)); checks[key]=bool(p.get('ok')) and not p.get('errors')
  if count is not None: checks[key+'_count']=len(p.get('checks',{}))==count
  evidence[key]={'ok':p.get('ok'),'check_count':len(p.get('checks',{})),'candidate_count':p.get('candidate_count'),'actions_taken':p.get('actions_taken')}
 cas_token=''
 for line in Path('/etc/octopus/cas-api.env').read_text().splitlines():
  if line.startswith('CAS_READ_TOKEN='): cas_token=line.split('=',1)[1]
 ap_token=Path('/etc/octopus/autopilot.token').read_text().strip()
 http_contract={
  'cas_anon':http('http://127.0.0.1:9540/cas/stats'),
  'cas_auth':http('http://127.0.0.1:9540/cas/stats',cas_token),
  'gateway_anon':http('http://127.0.0.1:9088/cas/stats'),
  'gateway_auth':http('http://127.0.0.1:9088/cas/stats',cas_token),
  'autopilot_anon':http('http://127.0.0.1:8787/system/status'),
  'autopilot_auth':http('http://127.0.0.1:8787/system/status',ap_token),
  'external_health':curl_http('https://api.autosklo.org.ua/health'),
  'external_privileged_anon':curl_http('https://api.autosklo.org.ua/system/status'),
  'external_cas':curl_http('https://api.autosklo.org.ua/cas/stats'),
 }
 evidence['http_contract']=http_contract
 checks['http_contract']=http_contract=={'cas_anon':401,'cas_auth':200,'gateway_anon':401,'gateway_auth':200,'autopilot_anon':401,'autopilot_auth':200,'external_health':200,'external_privileged_anon':401,'external_cas':404}
 cf=Path('/etc/systemd/system/cloudflared.service').read_text(errors='replace')
 checks['cloudflared_no_inline_token']=not re.search(r'--token\s+\S+',cf) and '--token-file /etc/cloudflared/octopus-main.token' in cf
 warnings.append('manual blocker: rotate Cloudflare named tunnel token account-side')
 ok=all(checks.values())
 now=datetime.now(timezone.utc); stamp=now.strftime('%Y%m%dT%H%M%SZ')
 trace_id=f'octo-{stamp}-release-verify-{secrets.token_hex(4)}'
 report={'timestamp':now.isoformat(),'trace_id':trace_id,'status':'pass_with_manual_blocker' if ok else 'fail','ok':ok,'read_only':True,'secret_values_emitted':False,'checks':checks,'warnings':warnings,'evidence':evidence}
 text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
 if a.output: a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(text)
 print(text if a.json else f"ok={ok} checks={sum(checks.values())}/{len(checks)} warnings={len(warnings)}")
 return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
