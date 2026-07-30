#!/usr/bin/env python3
import json, os, subprocess, hashlib
from datetime import datetime, timezone
from pathlib import Path
R=Path('/root/agents/-Octopus'); B=R/'skills/core/money-earner-orchestrator'; D=B/'data'; CFG=R/'config'
POL=json.loads((CFG/'execution_policy.json').read_text()); OPP=json.loads((D/'opportunity_aggregate_latest.json').read_text())
if os.environ.get('OCTOPUS_EXTERNAL_EFFECT_LOCKED')!='1': raise SystemExit('global lock required')
policy=POL.get('github_write_actions',{})
if not policy.get('enabled') or not policy.get('allow_third_party_repositories'): raise SystemExit('third-party publications disabled')
state_path=D/'third_party_publication_state.json'
try: state=json.loads(state_path.read_text())
except Exception: state={'publications':[]}
today=datetime.now(timezone.utc).date().isoformat()
today_rows=[x for x in state.get('publications',[]) if str(x.get('ts','')).startswith(today)]
remaining=max(0,int(policy.get('max_publications_per_day',5))-len(today_rows))
verified=OPP.get('opportunities',[]) if int(OPP.get('live_verified_total',0) or 0)>0 else []
results=[]
env={**os.environ,'GH_TOKEN':Path('/root/.gh_token').read_text().strip()}
for item in verified:
 if remaining<=0: break
 repo=item.get('repository') or item.get('repo')
 issue=item.get('issue_number') or item.get('number')
 if not repo or not issue: continue
 if any(x.get('repository')==repo for x in today_rows): continue
 title=str(item.get('title') or '')
 reward=item.get('reward') or item.get('reward_usd') or 'указана в issue'
 marker='octopus-bounty-'+hashlib.sha256(f'{repo}#{issue}'.encode()).hexdigest()[:16]
 if any(x.get('idempotency_key')==marker for x in state.get('publications',[])): continue
 # Verify live issue and that it is open before writing.
 check=subprocess.run(['gh','api',f'repos/{repo}/issues/{issue}'],capture_output=True,text=True,env=env)
 if check.returncode!=0: continue
 live=json.loads(check.stdout)
 if live.get('state')!='open' or live.get('pull_request'): continue
 body=(f'Octopus automation reviewed this bounty as a potential contribution target. '
       f'Issue: {title}. Reward: {reward}. '
       'I am preparing a scoped implementation and will avoid duplicate work. '
       f'<!-- {marker} -->')
 # Do not comment if marker already exists in issue comments.
 comments=subprocess.run(['gh','api',f'repos/{repo}/issues/{issue}/comments','--paginate'],capture_output=True,text=True,env=env)
 if comments.returncode==0 and marker in comments.stdout: continue
 post=subprocess.run(['gh','issue','comment',str(issue),'--repo',repo,'--body',body],capture_output=True,text=True,env=env)
 rec={'ts':datetime.now(timezone.utc).isoformat(),'repository':repo,'issue_number':issue,'idempotency_key':marker,'ok':post.returncode==0,'error':post.stderr[-300:] if post.returncode else ''}
 results.append(rec)
 if post.returncode==0:
  state.setdefault('publications',[]).append(rec); remaining-=1
state['publications']=state.get('publications',[])[-500:]
state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
out={'generated_at':datetime.now(timezone.utc).isoformat(),'eligible_verified':len(verified),'attempted':len(results),'published':sum(1 for x in results if x['ok']),'results':results}
(D/'third_party_publication_latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
