#!/usr/bin/env python3
import argparse,json,uuid,fcntl,tempfile,os
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/agents/-Octopus'); B=R/'skills/core/money-earner-orchestrator'; D=B/'data'; Q=D/'income_customer_requests.json'; L=D/'income_customer_requests.lock'
def load(p,d):
 try:return json.loads(p.read_text())
 except Exception:return d
def save(p,d):
 fd,tmp=tempfile.mkstemp(prefix=p.name+'.',dir=str(p.parent))
 with os.fdopen(fd,'w') as f: json.dump(d,f,ensure_ascii=False,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
 os.replace(tmp,p)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--customer-id',required=True); ap.add_argument('--plan',choices=['free','starter','pro'],required=True); ap.add_argument('--payment-status',choices=['not_required','pending','confirmed','budget_approved'],required=True); ap.add_argument('--idempotency-key',required=True); a=ap.parse_args()
 L.touch(exist_ok=True)
 with L.open('r+') as lf:
  fcntl.flock(lf.fileno(),fcntl.LOCK_EX); q=load(Q,{'version':1,'requests':[]})
  old=next((x for x in q['requests'] if x.get('idempotency_key')==a.idempotency_key),None)
  if old: print(json.dumps(old,ensure_ascii=False)); return
  req={'request_id':str(uuid.uuid4()),'created_at':datetime.now(timezone.utc).isoformat(),'customer_id':a.customer_id,'plan':a.plan,'payment_status':a.payment_status,'idempotency_key':a.idempotency_key,'status':'received'}
  q['requests'].append(req); save(Q,q); print(json.dumps(req,ensure_ascii=False))
if __name__=='__main__':main()
