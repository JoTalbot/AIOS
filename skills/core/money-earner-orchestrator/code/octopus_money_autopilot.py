#!/usr/bin/env python3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import json, os, subprocess
B=Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator'); D=B/'data'; REPORT=D/'autopilot_latest.json'

def run(name, cmd, timeout=170):
    try:
        p=subprocess.run(cmd,cwd=B,capture_output=True,text=True,timeout=timeout,env={**os.environ,'OCTOPUS_AUTOPILOT':'1','OCTOPUS_BATCH_MODE':'parallel_waves'})
        return {'name':name,'ok':p.returncode==0,'code':p.returncode,'stdout':p.stdout[-1200:],'stderr':p.stderr[-1200:]}
    except Exception as e:return {'name':name,'ok':False,'error':str(e)[:300]}

def wave(wave_id,tasks,workers=8,critical=False):
    started=datetime.now(timezone.utc).isoformat(); rows=[]
    with ThreadPoolExecutor(max_workers=min(workers,len(tasks))) as ex:
        fs={ex.submit(run,n,c):n for n,c in tasks.items()}
        for f in as_completed(fs): rows.append(f.result())
    ok=all(x.get('ok') for x in rows)
    return {'wave_id':wave_id,'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'parallel':True,'workers':min(workers,len(tasks)),'critical':critical,'ok':ok,'tasks':rows}

def main():
    py='/usr/bin/python3'
    waves=[]
    waves.append(wave('wave_1_discovery_probe',{
      'opportunities':[py,str(B/'code/opportunity_aggregate_runner.py')],
      'faucet_probe':[py,str(B/'code/playwright_faucet_claimer.py'),'--faucets','btcpop-faucet,dash-faucet-com,cryptofaucet-club,cryptofaucet-ltc','--probe-only'],
      'paper_trade':[py,str(B/'code/run.py'),'--json'],
      'income_portfolio':[py,str(B/'code/income_portfolio_batch.py')]
    },8,False))
    waves.append(wave('wave_2_accounting_control',{
      'currency_ledger':[py,str(B/'code/currency_ledger.py')],
      'source_roi_gate':[py,str(B/'code/source_roi_gate.py')],
      'source_control_plane':[py,str(B/'code/source_control_plane.py')],
      'service_pipeline':[py,str(B/'code/service_pipeline.py')],
      'captcha_budget_audit':[py,str(B/'code/captcha_budget_audit.py')],
      'roadmap_audit':[py,str(B/'code/roadmap_audit_batch.py')]
    },8,True))
    if not waves[-1]['ok']:
        report={'generated_at':datetime.now(timezone.utc).isoformat(),'mode':'batch_of_parallel_waves','waves':waves,'ok':False,'stopped_after':waves[-1]['wave_id']}
        REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'ok':False,'stopped_after':waves[-1]['wave_id']})); raise SystemExit(1)
    waves.append(wave('wave_3_health_scaling',{
      'scaling_allocator':[py,str(B/'code/scaling_allocator.py')],
      'metrics_snapshot':[py,str(B/'code/metrics_snapshot.py')],
      'timer_health':[py,str(B/'code/timer_health.py')],
      'process_guard':[py,str(B/'code/bounded_process_guard.py')]
    },8,False))
    waves.append(wave('wave_4_summary',{
      'self_sufficiency_status':[py,str(B/'code/self_sufficiency_status.py')],
      'service_offer_report':[py,str(B/'code/service_offer_report.py')]
    },4,True))
    # Daily summary depends on all previous wave outputs.
    final=run('daily_summary',[py,str(B/'code/daily_summary.py')]); waves.append({'wave_id':'wave_5_final_barrier','parallel':False,'workers':1,'critical':True,'ok':final.get('ok',False),'tasks':[final]})
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'mode':'batch_of_parallel_waves','wave_count':len(waves),'waves':waves,'ok':all(w.get('ok') for w in waves)}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'ok':report['ok'],'waves':{w['wave_id']:w['ok'] for w in waves}},ensure_ascii=False)); raise SystemExit(0 if report['ok'] else 1)
if __name__=='__main__':main()
