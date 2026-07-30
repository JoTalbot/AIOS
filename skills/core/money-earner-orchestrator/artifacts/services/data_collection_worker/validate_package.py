#!/usr/bin/env python3
import json
from pathlib import Path
root=Path(__file__).resolve().parent
for name in ('offer.json','sample_order.json'):
    data=json.loads((root/name).read_text())
    assert data.get('service_id')==root.name
assert json.loads((root/'offer.json').read_text()).get('payment_gate_required') is True
print('OK',root.name)
