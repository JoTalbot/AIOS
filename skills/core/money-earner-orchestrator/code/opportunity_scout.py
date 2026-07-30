#!/usr/bin/env python3
import argparse,json,re,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
B=Path(__file__).resolve().parents[1]
OUT=B/"data/opportunity_scout_latest.json"
TOKEN=Path("/root/.gh_token")
SKILLS={"python":3,"linux":3,"systemd":3,"docker":2,"api":2,"github actions":3,"monitoring":3,"sre":4,"automation":3,"playwright":2,"bash":2,"kubernetes":2,"terraform":2}
RISKS={"crypto":2,"wallet":2,"trading":3,"investment":4,"adult":5,"gambling":5,"exploit":4,"malware":5}
def extract_reward(text):
    vals=[]
    for m in re.finditer(r"(?:\$|USD\s*)(\d{1,6}(?:[.,]\d{1,2})?)",text,re.I):
        try: vals.append(float(m.group(1).replace(",",".")))
        except ValueError: pass
    return max(vals) if vals else None
def score(text,amount,comments):
    x=text.lower(); s=10+min(30,int(amount/25)); reasons=[f"explicit_reward_usd={amount:g}"]
    for k,w in SKILLS.items():
        if k in x: s+=w; reasons.append("skill:"+k)
    for k,w in RISKS.items():
        if k in x: s-=w; reasons.append("risk:"+k)
    if comments==0: s+=2; reasons.append("low_competition")
    return s,reasons
def fetch_json(url,token):
    h={"Accept":"application/vnd.github+json","User-Agent":"octopus-opportunity-scout"}
    if token: h["Authorization"]="Bearer "+token
    req=urllib.request.Request(url,headers=h)
    with urllib.request.urlopen(req,timeout=25) as r:
        return json.loads(r.read().decode())
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--limit",type=int,default=30); ap.add_argument("--json",action="store_true"); args=ap.parse_args()
    token=TOKEN.read_text().strip() if TOKEN.exists() else ""
    queries=[
      "is:issue is:open (bounty OR paid OR reward) in:title,body",
      "is:issue is:open label:bounty",
      "is:issue is:open label:\"💰 bounty\""
    ]
    seen={}; errors=[]
    for q in queries:
        try:
            url="https://api.github.com/search/issues?"+urllib.parse.urlencode({"q":q,"sort":"updated","order":"desc","per_page":100})
            for item in fetch_json(url,token).get("items",[]): seen[item["html_url"]]=item
        except Exception as e: errors.append(str(e)[:180])
    rows=[]
    for item in seen.values():
        text=(item.get("title") or "")+" "+(item.get("body") or "")+" "+" ".join(x.get("name","") for x in item.get("labels",[]))
        amount=extract_reward(text)
        deny_terms=("container escape","command injection","credential theft","cloud takeover","sandbox escape","hardcoded aws keys","malware","rce","remote code execution","exploit chain")
        if any(term in text.lower() for term in deny_terms):
            continue
        if amount is None or amount<5:
            continue
        repo_url=item.get("repository_url") or ""
        blocked_repo=("claude-builders-bounty/claude-builders-bounty" in repo_url or "xevrion-v2/agent-playground" in repo_url)
        if blocked_repo or item.get("comments",0)>50:
            continue
        sc,reasons=score(text,amount,item.get("comments",0))
        rows.append({"source":"github","score":sc,"reward_usd":amount,"title":item.get("title"),"url":item.get("html_url"),"comments":item.get("comments",0),"updated_at":item.get("updated_at"),"reasons":reasons})
    rows.sort(key=lambda x:(x["score"],x["reward_usd"]),reverse=True)
    report={"generated_at":datetime.now(timezone.utc).isoformat(),"mode":"read_only_strict_paid","found":len(rows),"errors":errors,"opportunities":rows[:args.limit]}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(report,ensure_ascii=False,indent=2) if args.json else f"found={len(rows)} errors={len(errors)} out={OUT}")
if __name__=="__main__": main()
