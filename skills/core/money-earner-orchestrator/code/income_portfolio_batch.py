#!/usr/bin/env python3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import json
R=Path('/root/agents/-Octopus'); B=R/'skills/core/money-earner-orchestrator'; D=B/'data'; A=B/'artifacts/income'; A.mkdir(parents=True,exist_ok=True)
portfolio=json.loads((R/'config/income_portfolio.json').read_text()); methods=portfolio['methods']
def prepare(m):
 p=A/m['id']; p.mkdir(parents=True,exist_ok=True); blockers=[]
 if m['kyc_required']: blockers.append('kyc_or_payout_account')
 if m['human_required']: blockers.append('human_profile_or_delivery')
 if m['cash_cost']>0: blockers.append('budget_approval')
 if m['server_fit']==0: blockers.append('hardware_not_supported')
 status='ready_to_build' if not blockers else ('blocked_external' if m['kyc_required'] or m['human_required'] else 'needs_budget')
 spec={'generated_at':datetime.now(timezone.utc).isoformat(),'method':m,'status':status,'blockers':blockers,'next_step':'build_mvp' if status=='ready_to_build' else 'complete_external_prerequisites','external_side_effects':False}
 (p/'plan.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n'); return {'id':m['id'],'tier':m['tier'],'status':status,'blockers':blockers,'score':m['priority_score']}
def run_wave(wid,items,workers=8):
 rows=[]
 with ThreadPoolExecutor(max_workers=min(workers,len(items)) or 1) as ex:
  fs={ex.submit(prepare,m):m['id'] for m in items}
  for f in as_completed(fs): rows.append(f.result())
 rows.sort(key=lambda x:x['score'],reverse=True); return {'wave_id':wid,'parallel':True,'workers':min(workers,len(items)),'ok':True,'rows':rows}
def main():
 waves=[]
 waves.append(run_wave('wave_1_p0',[m for m in methods if m['tier']=='P0'],8))
 waves.append(run_wave('wave_2_p1',[m for m in methods if m['tier']=='P1'],8))
 waves.append(run_wave('wave_3_p2_inventory',[m for m in methods if m['tier']=='P2'],8))
 rows=[r for w in waves for r in w['rows']]
 summary={'generated_at':datetime.now(timezone.utc).isoformat(),'mode':'batch_of_parallel_waves','workers_per_wave':8,'portfolio_total':len(methods),'prepared':len(rows),'ready_to_build':sum(x['status']=='ready_to_build' for x in rows),'blocked_external':sum(x['status']=='blocked_external' for x in rows),'needs_budget':sum(x['status']=='needs_budget' for x in rows),'waves':[{k:v for k,v in w.items() if k!='rows'}|{'count':len(w['rows'])} for w in waves],'priority_queue':sorted(rows,key=lambda x:x['score'],reverse=True)[:25]}
 (D/'income_portfolio_batch_latest.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
