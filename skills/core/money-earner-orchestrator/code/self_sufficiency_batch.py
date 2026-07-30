#!/usr/bin/env python3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import json, subprocess, os
B=Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator'); D=B/'data'

def run(name, script, timeout=170):
    try:
        p=subprocess.run(['/usr/bin/python3',str(B/'code'/script)],cwd=B,capture_output=True,text=True,timeout=timeout,env={**os.environ,'OCTOPUS_BATCH_MODE':'parallel'})
        return {'name':name,'ok':p.returncode==0,'code':p.returncode,'stdout':p.stdout[-1000:],'stderr':p.stderr[-1000:]}
    except Exception as e:return {'name':name,'ok':False,'error':str(e)[:300]}

def wave(tasks,workers=8):
    out=[]
    with ThreadPoolExecutor(max_workers=min(workers,len(tasks))) as ex:
        fs={ex.submit(run,n,s):n for n,s in tasks.items()}
        for f in as_completed(fs):out.append(f.result())
    return out

def main():
    results=[]
    results+=wave({'currency_ledger':'currency_ledger.py','source_roi_gate':'source_roi_gate.py','source_control_plane':'source_control_plane.py','service_pipeline':'service_pipeline.py','captcha_budget_audit':'captcha_budget_audit.py','opportunities':'opportunity_aggregate_runner.py'})
    results+=wave({'scaling_allocator':'scaling_allocator.py','roadmap_audit':'roadmap_audit_batch.py','metrics_snapshot':'metrics_snapshot.py','timer_health':'timer_health.py'})
    results.append(run('self_sufficiency_status','self_sufficiency_status.py'))
    results.append(run('daily_summary','daily_summary.py'))
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'mode':'parallel_dependency_waves','workers':8,'tasks':results,'ok':all(x.get('ok') for x in results)}
    (D/'self_sufficiency_batch_latest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'ok':report['ok'],'tasks':{x['name']:x.get('ok',False) for x in results}},ensure_ascii=False))
    raise SystemExit(0 if report['ok'] else 1)
if __name__=='__main__':main()
