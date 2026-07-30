#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
R=Path('/root/agents/-Octopus'); B=R/'skills/core/money-earner-orchestrator'; D=B/'data'
def load(p,d):
 try:return json.loads(Path(p).read_text())
 except Exception:return d
budget=load(D/'daily_captcha_budget.json',{}); audit=load(D/'captcha_budget_audit_latest.json',{}); opp=load(D/'opportunity_aggregate_latest.json',{}); metrics=load(D/'metrics_snapshot_latest.json',{}); ra=load(D/'roadmap_audit_latest.json',{}); cur=load(D/'currency_ledger_latest.json',{}); svc=load(D/'service_pipeline_latest.json',{}); ctrl=load(D/'source_control_plane_latest.json',{}); scale=load(D/'scaling_allocator_latest.json',{})
confirmed_usd=float(cur.get('assets',{}).get('USD',{}).get('confirmed',0) or 0); confirmed_sats=float(cur.get('assets',{}).get('BTC_SATS',{}).get('confirmed',0) or 0); variable=float(budget.get('spent_usd',0) or 0); ratio=(confirmed_usd/variable) if variable>0 else (999 if confirmed_usd>0 else 0)
verified=int(opp.get('live_verified_total',0) or 0); audit_errors=len(ra.get('errors',[])); compliant=bool(audit.get('compliant',False)); paid_jobs=int(svc.get('summary',{}).get('paid',0) or 0); delivered=int(svc.get('summary',{}).get('delivered',0) or 0); active_sources=sum(1 for x in ctrl.get('sources',{}).values() if x.get('state')=='ACTIVE')
phase1=audit_errors==0 and compliant
phase2=phase1 and ratio>=1.25 and (confirmed_usd>0 or confirmed_sats>0)
phase3=phase2 and active_sources>=2
phase4=phase3 and paid_jobs>=3 and delivered>=3
phase5=phase4 and bool(scale.get('scaling_enabled'))
phase6=phase5 and active_sources>=3 and ratio>=1.25
level='L4' if phase6 else 'L3' if phase5 else 'L2' if phase4 else 'L1' if phase2 else 'L0'
statuses={'phase_1_accounting':'complete' if phase1 else 'active','phase_2_roi':'complete' if phase2 else ('active' if phase1 else 'pending'),'phase_3_income_sources':'complete' if phase3 else ('active' if phase2 else 'pending'),'phase_4_services':'complete' if phase4 else ('active' if phase3 else 'pending'),'phase_5_scale':'complete' if phase5 else ('active' if phase4 else 'pending'),'phase_6_self_sufficiency':'complete' if phase6 else ('active' if phase5 else 'pending')}
blockers=[]
if confirmed_usd<=0 and confirmed_sats<=0:blockers.append('no_confirmed_income')
if verified<=0:blockers.append('no_verified_bounties')
if active_sources<2:blockers.append('fewer_than_two_active_income_sources')
if paid_jobs<3:blockers.append('fewer_than_three_paid_jobs')
out={'generated_at':datetime.now(timezone.utc).isoformat(),'current_level':level,'phase_status':statuses,'kpi':{'confirmed_usd':confirmed_usd,'confirmed_sats':confirmed_sats,'variable_cost_usd':variable,'variable_cost_coverage_ratio':round(ratio,4),'captcha_policy_compliant':compliant,'audit_errors':audit_errors,'verified_bounties':verified,'active_income_sources':active_sources,'paid_jobs':paid_jobs,'delivered_jobs':delivered,'paper_realized_pnl_usd':metrics.get('paper_realized_pnl_usd')},'blockers':blockers,'next_actions':['first_confirmed_non_faucet_payout','verified_bounty_candidate','first_paid_service_order','seven_day_positive_roi']}
(D/'self_sufficiency_status_latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(out,ensure_ascii=False))
