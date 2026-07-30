from __future__ import annotations
import fcntl, json
from contextlib import contextmanager
from pathlib import Path
from captcha_budget_atomic import atomic_try_reserve
B=Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator')
CFG=B/'config/faucet_config.json'; BUDGET=B/'data/daily_captcha_budget.json'; LOCK=B/'data/locks/external_side_effects.lock'
def _cfg():
    try:return json.loads(CFG.read_text()).get('captcha',{})
    except Exception:return {}
@contextmanager
def paid_captcha_slot(source:str,cost_usd:float|None=None):
    cfg=_cfg()
    if not cfg.get('auto_paid_enabled',False): raise RuntimeError('paid_captcha_disabled')
    cost=float(cost_usd if cost_usd is not None else cfg.get('max_cost_per_solve_usd',0.003))
    max_daily=float(cfg.get('max_daily_budget_usd',0.5))
    LOCK.parent.mkdir(parents=True,exist_ok=True)
    with LOCK.open('a+') as lf:
        try: fcntl.flock(lf.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError('external_effect_lock_busy')
        ok,state=atomic_try_reserve(BUDGET,cost,max_daily,source=source,solves=1)
        if not ok: raise RuntimeError('daily_captcha_budget_rejected')
        yield {'cost_usd':cost,'budget':state}
