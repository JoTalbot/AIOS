#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

B = Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator')
p = B / 'data/income_sales_leads.jsonl'
rows = []
if p.exists():
    for line in p.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            pass

def is_canary(item):
    return (
        bool(item.get('test_canary'))
        or str(item.get('idempotency_key', '')).startswith('canary-')
        or str(item.get('contact', '')).endswith('@example.invalid')
    )

commercial = [x for x in rows if not is_canary(x)]
canaries = [x for x in rows if is_canary(x)]
out = {
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'total_records': len(rows),
    'commercial_total': len(commercial),
    'canary_total': len(canaries),
    'awaiting_review': sum(x.get('status') == 'awaiting_review' for x in commercial),
    'pending_payment': sum(x.get('payment_status') == 'pending' for x in commercial),
    'approved': sum(x.get('payment_status') in ('confirmed', 'budget_approved') for x in commercial),
    'auto_execute': False,
    'canaries_excluded_from_kpi': True,
}
(B / 'data/income_sales_status_latest.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + '\n'
)
print(json.dumps(out, ensure_ascii=False))
