#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
R = Path('/root/agents/-Octopus')
B = R / 'skills/core/money-earner-orchestrator'
D = B / 'data'

def load(path, default):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return default

catalog = load(R / 'config/service_catalog.json', {'services': []})
queue = load(D / 'service_order_queue.json', {'orders': []})
service_ids = {item['id'] for item in catalog.get('services', [])}
summary = {
    'received': 0,
    'validated': 0,
    'rejected': 0,
    'payment_pending': 0,
    'paid': 0,
    'delivered': 0,
}
checked = []
for order in queue.get('orders', []):
    summary['received'] += 1
    valid = order.get('service_id') in service_ids and bool(order.get('idempotency_key'))
    payment_status = order.get('payment_status', 'pending')
    requested_status = order.get('status', 'received')
    if not valid:
        effective_status = 'rejected'
        summary['rejected'] += 1
    else:
        summary['validated'] += 1
        paid = payment_status in ('confirmed', 'budget_approved')
        if requested_status == 'delivered' and paid:
            effective_status = 'delivered'
            summary['delivered'] += 1
        elif paid:
            effective_status = 'paid'
            summary['paid'] += 1
        else:
            effective_status = 'payment_pending'
            summary['payment_pending'] += 1
    checked.append({
        **order,
        'validation': 'ok' if valid else 'invalid',
        'effective_status': effective_status,
        'payment_gate_passed': payment_status in ('confirmed', 'budget_approved'),
    })

output = {
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'summary': summary,
    'orders': checked,
    'auto_execution': False,
    'execution_requires_payment_gate': True,
}
(D / 'service_pipeline_latest.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(summary, ensure_ascii=False))
