#!/usr/bin/env python3
import json,secrets,hashlib,fcntl,tempfile,os
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/agents/-Octopus'); B=R/'skills/core/money-earner-orchestrator'; D=B/'data'; CFG=R/'config'; Q=D/'income_customer_requests.json'; K=CFG/'income_mvp_api_keys.json'; OUT=D/'income_key_deliveries'; LOCK=D/'income_key_issuer.lock'
OUT.mkdir(exist_ok=True,mode=0o700)
def load(p,d):
 try:return json.loads(p.read_text())
 except Exception:return d
def save(p,d,mode=None):
 fd,tmp=tempfile.mkstemp(prefix=p.name+'.',dir=str(p.parent))
 with os.fdopen(fd,'w') as f: json.dump(d,f,ensure_ascii=False,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
 os.replace(tmp,p)
 if mode is not None: p.chmod(mode)
LOCK.touch(exist_ok=True)
with LOCK.open('r+') as lf:
 fcntl.flock(lf.fileno(),fcntl.LOCK_EX); q=load(Q,{'version':1,'requests':[]}); keys=load(K,{'version':1,'keys':[]}); issued=[]
 for r in q.get('requests',[]):
  if r.get('status')=='issued': continue
  plan=r.get('plan'); pay=r.get('payment_status')
  allowed=(plan=='free' and pay=='not_required') or (plan in ('starter','pro') and pay in ('confirmed','budget_approved'))
  if not allowed: continue
  name='customer-'+r['request_id'][:8]
  if any(x.get('request_id')==r['request_id'] for x in keys.get('keys',[])): r['status']='issued'; continue
  raw='oct_'+secrets.token_urlsafe(32); rec={'name':name,'plan':plan,'enabled':True,'key_sha256':hashlib.sha256(raw.encode()).hexdigest(),'created_at':datetime.now(timezone.utc).isoformat(),'request_id':r['request_id'],'customer_id':r['customer_id']}
  keys.setdefault('keys',[]).append(rec); delivery=OUT/(r['request_id']+'.json'); delivery.write_text(json.dumps({'request_id':r['request_id'],'customer_id':r['customer_id'],'plan':plan,'api_key':raw,'created_at':rec['created_at']},ensure_ascii=False,indent=2)+'\n'); delivery.chmod(0o600); r['status']='issued'; r['issued_at']=rec['created_at']; issued.append({'request_id':r['request_id'],'plan':plan,'delivery_file':str(delivery)})
 save(K,keys,0o600); save(Q,q,0o600)
 print(json.dumps({'issued_count':len(issued),'issued':[{'request_id':x['request_id'],'plan':x['plan']} for x in issued]},ensure_ascii=False))
