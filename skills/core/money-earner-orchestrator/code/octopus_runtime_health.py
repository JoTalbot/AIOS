#!/usr/bin/env python3
import json, subprocess
from datetime import datetime, timezone
from pathlib import Path
B=Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator'); D=B/'data'
required=['octopus-income-mvp.service','octopus-money-autopilot.timer','octopus-autonomous-agent.timer','octopus-all-vectors-dev.timer','octopus-skill-evolution.timer','octopus-telegram-drift-guard.timer','octopus-income-customer-pipeline.timer','octopus-income-pages-sync.timer','octopus-all-vectors-batch.timer','octopus-skill-index-drift.timer','octopus-traff-health.timer']
rows=[]
for unit in required:
    p=subprocess.run(['systemctl','show',unit,'-p','ActiveState','-p','SubState','-p','Result','--no-pager'],capture_output=True,text=True,timeout=10)
    row={'unit':unit,'query_ok':p.returncode==0}
    for line in p.stdout.splitlines():
        if '=' in line:
            k,v=line.split('=',1); row[k]=v
    row['healthy']=row.get('ActiveState')=='active' and row.get('Result','success') in ('success','')
    rows.append(row)
p=subprocess.run(['systemctl','--failed','--no-legend','--plain'],capture_output=True,text=True,timeout=10)
failed_octopus=[line for line in p.stdout.splitlines() if 'octopus-' in line]
drift_path=D/'skill_index_drift_latest.json'
try:
    skill_index_drift=json.loads(drift_path.read_text())
    generated=datetime.fromisoformat(skill_index_drift['generated_at'].replace('Z','+00:00'))
    age_sec=max(0,(datetime.now(timezone.utc)-generated).total_seconds())
except Exception:
    skill_index_drift={'healthy':False,'changed':None,'error':'missing_or_invalid_report'}; age_sec=None
fresh=age_sec is not None and age_sec<=2700
traff_path=Path('/root/agents/projects/traff/data/health_latest.json')
try:
    traff=json.loads(traff_path.read_text())
    traff_generated=datetime.fromisoformat(traff['generated_at'].replace('Z','+00:00'))
    traff_age_sec=max(0,(datetime.now(timezone.utc)-traff_generated).total_seconds())
except Exception:
    traff={'healthy':False,'service_total':None,'service_ok':None,'financial_guard_ok':False}; traff_age_sec=None
traff_fresh=traff_age_sec is not None and traff_age_sec<=1200
traff_ok=traff.get('healthy') is True and traff.get('service_ok')==traff.get('service_total') and traff.get('financial_guard_ok') is True and traff_fresh
out={'generated_at':datetime.now(timezone.utc).isoformat(),'scope':'octopus_with_managed_projects','units':rows,'failed_octopus_units':failed_octopus,'skill_index_drift':{'healthy':skill_index_drift.get('healthy'),'changed':skill_index_drift.get('changed'),'fresh':fresh,'age_sec':round(age_sec,1) if age_sec is not None else None,'max_age_sec':2700,'report':str(drift_path)},'traff_project':{'healthy':traff.get('healthy'),'fresh':traff_fresh,'age_sec':round(traff_age_sec,1) if traff_age_sec is not None else None,'max_age_sec':1200,'service_total':traff.get('service_total'),'service_ok':traff.get('service_ok'),'financial_guard_ok':traff.get('financial_guard_ok'),'report':str(traff_path)},'healthy':all(x['healthy'] for x in rows) and not failed_octopus and skill_index_drift.get('healthy') is True and skill_index_drift.get('changed') is False and fresh and traff_ok}
(D/'octopus_runtime_health_latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'healthy':out['healthy'],'units':len(rows),'failed_octopus_units':len(failed_octopus),'skill_index_fresh':fresh},ensure_ascii=False))
raise SystemExit(0 if out['healthy'] else 1)
