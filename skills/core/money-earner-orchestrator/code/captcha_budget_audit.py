#!/usr/bin/env python3
import json,re
from datetime import datetime,timezone
from pathlib import Path
B=Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator'); C=B/'code'; D=B/'data'
paid=[]; unguarded=[]
for p in C.glob('*.py'):
    s=p.read_text(errors='ignore')
    if any(x in s for x in ('api.2captcha.com/createTask','api.2captcha.com/in.php','api.capsolver.com/createTask')):
        paid.append(p.name)
        if not any(x in s for x in ('atomic_try_reserve','CaptchaSolver(','requires with_external_effect_lock.sh')):
            unguarded.append(p.name)
b=json.loads((D/'daily_captcha_budget.json').read_text())
c=json.loads((B/'config/faucet_config.json').read_text()).get('captcha',{})
out={'generated_at':datetime.now(timezone.utc).isoformat(),'paid_callsite_files':paid,'unguarded_files':unguarded,'budget':b,'limits':{'auto_paid_enabled':c.get('auto_paid_enabled'),'max_daily_budget_usd':c.get('max_daily_budget_usd'),'max_cost_per_solve_usd':c.get('max_cost_per_solve_usd')},'compliant':not unguarded and float(b.get('spent_usd',0))<=float(c.get('max_daily_budget_usd',0))}
(D/'captcha_budget_audit_latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
