#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
B=Path(__file__).resolve().parents[1]; D=B/'data'; OUT=D/'roadmap_audit_latest.json'
def load(n,d):
 try:return json.loads((D/n).read_text())
 except Exception:return d
def stability():
 p=subprocess.run(['systemctl','show','octopus-money-autopilot.service','-p','Result','-p','ExecMainStatus','-p','ActiveState','--no-pager'],capture_output=True,text=True,timeout=10)
 orphans=subprocess.run(['pgrep','-af','octopus_money_autopilot|playwright_faucet_claimer|opportunity_aggregate_runner'],capture_output=True,text=True,timeout=10)
 return {'service':p.stdout.strip(),'orphan_candidates':[x for x in orphans.stdout.splitlines() if 'pgrep -af' not in x]}
def accounting():
 f=load('faucet_ledger.json',{'runs':[]}); e=load('earnings_ledger.json',{}); b=load('daily_captcha_budget.json',{})
 future=[]; duplicate_ts=[]; seen=set()
 now=datetime.now(timezone.utc)
 for r in f.get('runs',[]):
  ts=r.get('ts','')
  if ts in seen: duplicate_ts.append(ts)
  seen.add(ts)
  try:
   if datetime.fromisoformat(ts)>now: future.append(ts)
  except Exception: pass
 return {'faucet_runs':len(f.get('runs',[])),'future_timestamps':future,'duplicate_timestamps':duplicate_ts,'captcha_spent_usd':b.get('spent_usd',0),'captcha_solves':b.get('solves',0),'paper_pnl_usd':e.get('paper',{}).get('realized_pnl_usd',0)}
def roi():
 b=load('daily_captcha_budget.json',{}); f=load('faucet_ledger.json',{'runs':[]}); e=load('earnings_ledger.json',{})
 claimed=sum(float(r.get('total_sats_claimed',0) or 0) for r in f.get('runs',[]))
 spent=float(b.get('spent_usd',0) or 0); pnl=float(e.get('paper',{}).get('realized_pnl_usd',0) or 0)
 return {'confirmed_sats':claimed,'captcha_spent_usd':spent,'paper_realized_pnl_usd':pnl,'captcha_roi_positive':claimed>0 and spent>0,'paper_stop_loss_distance_usd':round(5-abs(min(0,pnl)),6),'recommendation':'block_paid_captcha' if spent>0 and claimed<=0 else 'continue_bounded'}
def integrations():
 s=load('faucet_integration_status.json',{})
 return {k:s.get(k,[]) for k in ('integrated','probe_ready','blocked','inactive')}
def bounties():
 x=load('opportunity_aggregate_latest.json',{})
 return {'raw':x.get('raw',{}),'live_verified_total':x.get('live_verified_total',0),'rejected':x.get('rejected',{}),'errors':x.get('errors',[])}
def main():
 jobs={'stability':stability,'accounting':accounting,'roi':roi,'integrations':integrations,'bounties':bounties}; out={}; errors=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
  fs={ex.submit(fn):name for name,fn in jobs.items()}
  for f,name in fs.items():
   try:out[name]=f.result()
   except Exception as e:errors.append({'task':name,'error':str(e)[:200]})
 report={'generated_at':datetime.now(timezone.utc).isoformat(),'mode':'parallel_read_only_audit','results':out,'errors':errors}
 OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'ok':not errors,'tasks':list(out),'errors':len(errors)}))
if __name__=='__main__':main()
