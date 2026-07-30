#!/usr/bin/env python3
import argparse,json,uuid,fcntl,os,tempfile
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/agents/-Octopus'); B=R/'skills/core/money-earner-orchestrator'; D=B/'data'; Q=D/'service_order_queue.json'; LOCK=D/'service_order_queue.lock'
def load(p,d):
 try:return json.loads(p.read_text())
 except Exception:return d
def atomic_save(p,d):
 fd,tmp=tempfile.mkstemp(prefix=p.name+'.',dir=str(p.parent))
 with os.fdopen(fd,'w') as f: json.dump(d,f,ensure_ascii=False,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
 os.replace(tmp,p)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--service-id',required=True); ap.add_argument('--requirements',required=True); ap.add_argument('--acceptance-criteria',required=True); ap.add_argument('--payment-status',choices=['pending','confirmed','budget_approved'],default='pending'); ap.add_argument('--idempotency-key',default=''); a=ap.parse_args()
 catalog=load(R/'config/service_catalog.json',{'services':[]}); ids={x['id'] for x in catalog['services']}
 if a.service_id not in ids: raise SystemExit('unknown service_id')
 idem=a.idempotency_key or str(uuid.uuid4()); LOCK.touch(exist_ok=True)
 with LOCK.open('r+') as lf:
  fcntl.flock(lf.fileno(),fcntl.LOCK_EX); q=load(Q,{'version':1,'orders':[]})
  if any(x.get('idempotency_key')==idem for x in q['orders']): raise SystemExit('duplicate idempotency_key')
  o={'order_id':str(uuid.uuid4()),'created_at':datetime.now(timezone.utc).isoformat(),'service_id':a.service_id,'requirements':a.requirements,'acceptance_criteria':a.acceptance_criteria,'payment_status':a.payment_status,'idempotency_key':idem,'status':'received'}
  q['orders'].append(o); atomic_save(Q,q); print(json.dumps(o,ensure_ascii=False))
if __name__=='__main__':main()
