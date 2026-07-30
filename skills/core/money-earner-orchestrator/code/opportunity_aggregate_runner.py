#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures, json, re, subprocess, urllib.request
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
B=Path(__file__).resolve().parents[1]
DATA=B/'data'; GH=DATA/'opportunity_batch_latest.json'; OUT=DATA/'opportunity_aggregate_latest.json'; TOKEN=Path('/root/.gh_token')
DENY=('exploit','injection','bypass','takeover','token leak','path traversal','idor','xss','csrf','malware','rce','privilege escalation','arbitrary file write','data leak','session fixation','clickjacking','redos','vulnerability')
SKILLS=('python','linux','docker','systemd','monitoring','automation','api','bash','typescript','documentation','github actions','kubernetes','terraform')
def gh_get(url):
    h={'Accept':'application/vnd.github+json','User-Agent':'octopus-opportunity-live-verify'}
    if TOKEN.exists(): h['Authorization']='Bearer '+TOKEN.read_text().strip()
    with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=25) as r: return json.loads(r.read().decode())
def github_batch():
    p=subprocess.run(['/usr/bin/python3',str(B/'code/opportunity_batch_runner.py'),'--workers','8','--limit','100'],cwd=B,capture_output=True,text=True,timeout=170)
    if p.returncode: raise RuntimeError((p.stderr or p.stdout)[-300:])
    return json.loads(GH.read_text())
def issuehunt_batch():
    req=urllib.request.Request('https://oss.issuehunt.io/issues',headers={'User-Agent':'Mozilla/5.0 Octopus read-only scout'})
    with urllib.request.urlopen(req,timeout=30) as r: h=r.read().decode('utf-8','replace')
    marker='__NEXT_DATA__ = '; start=h.find(marker)
    if start<0: raise RuntimeError('IssueHunt NEXT_DATA not found')
    start+=len(marker); end=h.find('</script>',start)
    if end<0: raise RuntimeError('IssueHunt NEXT_DATA closing script not found')
    d,_=json.JSONDecoder().raw_decode(h[start:end].lstrip()); issues=d.get('props',{}).get('pageProps',{}).get('issues',[])
    rows=[]
    for x in issues:
        if x.get('githubState')!='open' or x.get('status') not in ('ready','open'): continue
        amount=float(x.get('depositAmount') or 0)/100.0
        if amount<10: continue
        text=((x.get('title') or '')+' '+(x.get('body') or '')).lower()
        if any(k in text for k in DENY): continue
        repo=f"{x.get('repositoryOwnerName','')}/{x.get('repositoryName','')}"; num=x.get('number')
        score=10+min(30,int(amount/25))+sum(2 for k in SKILLS if k in text)
        rows.append({'source':'issuehunt','score':score,'reward_usd':amount,'title':x.get('title'),'url':f'https://github.com/{repo}/issues/{num}','repo':repo,'number':num,'comments':x.get('pullRequestCount',0),'reasons':[f'funded_usd={amount:g}','issuehunt_open_ready']})
    return {'raw':len(issues),'eligible':len(rows),'opportunities':rows}
def parse_issue_url(url):
    m=re.match(r'https://github\.com/([^/]+/[^/]+)/issues/(\d+)',url or '')
    return (m.group(1),int(m.group(2))) if m else (None,None)
def live_verify(row):
    repo,num=parse_issue_url(row.get('url'))
    if not repo: return None, 'bad_issue_url'
    issue=gh_get(f'https://api.github.com/repos/{repo}/issues/{num}')
    meta=gh_get(f'https://api.github.com/repos/{repo}')
    if issue.get('state')!='open': return None,'issue_closed'
    if meta.get('archived') or meta.get('disabled'): return None,'repo_inactive'
    if meta.get('stargazers_count',0)<10: return None,'low_trust_repo'
    src=(row.get('title') or '').lower(); live=(issue.get('title') or '').lower()
    ratio=SequenceMatcher(None,src,live).ratio()
    if row.get('source')!='github' and ratio<0.55: return None,'title_mismatch'
    out=dict(row)
    out.update({'repo':repo,'number':num,'live_title':issue.get('title'),'live_updated_at':issue.get('updated_at'),'repo_stars':meta.get('stargazers_count',0),'repo_archived':meta.get('archived',False),'title_match':round(ratio,3),'live_verified':True})
    return out,None
def main():
    errors=[]; parts=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        jobs={'github':ex.submit(github_batch),'issuehunt':ex.submit(issuehunt_batch)}
        for name,f in jobs.items():
            try: parts.append((name,f.result()))
            except Exception as e: errors.append({'source':name,'phase':'collect','error':str(e)[:240]})
    rows=[]; raw={}; eligible={}
    for name,p in parts:
        raw[name]=p.get('raw',0); eligible[name]=p.get('eligible',len(p.get('opportunities',[])))
        for x in p.get('opportunities',[]):
            y=dict(x); y.setdefault('source',name); rows.append(y)
    rows=list({x.get('url'):x for x in rows if x.get('url')}.values())
    verified=[]; rejected={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        fs={ex.submit(live_verify,x):x for x in rows}
        for f,x in fs.items():
            try:
                item,reason=f.result()
                if item: verified.append(item)
                else: rejected[reason]=rejected.get(reason,0)+1
            except Exception as e:
                errors.append({'source':x.get('source'),'phase':'live_verify','url':x.get('url'),'error':str(e)[:180]})
    verified.sort(key=lambda x:(x.get('score',0),x.get('reward_usd',0),x.get('repo_stars',0)),reverse=True)
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'mode':'parallel_multi_source_live_verified_read_only','workers':8,'sources':['github','issuehunt'],'raw':raw,'eligible_preverify':eligible,'live_verified_total':len(verified),'rejected':rejected,'errors':errors,'opportunities':verified[:100]}
    DATA.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f"sources=2 live_verified={len(verified)} rejected={sum(rejected.values())} errors={len(errors)}")
if __name__=='__main__': main()
