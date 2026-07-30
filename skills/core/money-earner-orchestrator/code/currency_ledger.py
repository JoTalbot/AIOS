#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
B=Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator'); D=B/'data'
def load(n,d):
 try:return json.loads((D/n).read_text())
 except Exception:return d
f=load('faucet_ledger.json',{'runs':[]}); b=load('daily_captcha_budget.json',{}); e=load('earnings_ledger.json',{})
assets={k:{'internal_balance':0.0,'withdrawable':0.0,'sent':0.0,'confirmed':0.0,'unit':k} for k in ['BTC_SATS','DOGE','LTC','DASH','USD']}
for r in f.get('runs',[]):
 coin=str(r.get('coin') or '').upper(); amt=float(r.get('amount_sats') or 0)
 if amt and (coin in ('BTC','SATS','') or r.get('faucet')=='lightningnetworkstores.com'):
  assets['BTC_SATS']['confirmed']+=amt if r.get('success') else 0
# Known internal DOGE balance remains separate and non-confirmed.
assets['DOGE']['internal_balance']=0.00625186
assets['USD']['confirmed']=0.0
out={'generated_at':datetime.now(timezone.utc).isoformat(),'policy':'confirmed_funds_only','assets':assets,'expenses':{'captcha_usd':float(b.get('spent_usd',0) or 0)},'paper':{'realized_pnl_usd':float(e.get('paper',{}).get('realized_pnl_usd',0) or 0),'counts_as_confirmed_income':False}}
(D/'currency_ledger_latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(out,ensure_ascii=False))
