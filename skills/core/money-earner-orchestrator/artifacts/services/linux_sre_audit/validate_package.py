#!/usr/bin/env python3
import json
from pathlib import Path
root=Path(__file__).resolve().parent
required={"offer.json":["service_id","title","price_usd","scope","acceptance_criteria","safety"],"sample_order.json":["service_id","order_id","idempotency_key","requirements","acceptance_criteria","payment_status"]}
for name,keys in required.items():
    data=json.loads((root/name).read_text())
    missing=[k for k in keys if k not in data]
    if missing: raise SystemExit(f"{name}: missing {missing}")
    if data.get("service_id") != root.name: raise SystemExit(f"{name}: service_id mismatch")
print(f"OK {root.name}")
