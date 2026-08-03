"""Тест CRM-сводки жизненного цикла продаж без ПД клиентов."""
from __future__ import annotations

import json


def test_crm_snapshot_hides_customer_fields_and_counts_pipeline(tmp_path):
    from aios_core.sales_lifecycle import SalesLifecycle

    data = tmp_path / "data"
    data.mkdir()
    (data / "sales_lifecycle.json").write_text(json.dumps([
        {"id": "a", "item": "Фара", "ttn": "111", "status": "awaiting_shipment", "amount": 1000,
         "customer_phone": "380000000000", "recipient": "Private Person", "updated_at": "2026-08-01T10:00:00+00:00"},
        {"id": "b", "item": "Капот", "ttn": "222", "status": "in_transit", "amount": 2500,
         "updated_at": "2026-08-02T10:00:00+00:00"},
        {"id": "c", "item": "Зеркало", "ttn": "333", "status": "delivered", "amount": 900,
         "updated_at": "2026-08-03T10:00:00+00:00"},
    ]), encoding="utf-8")
    (data / "sales_tasks.json").write_text(json.dumps([
        {"sale_id": "a", "status": "open"}, {"sale_id": "b", "status": "done"},
    ]), encoding="utf-8")

    snapshot = SalesLifecycle(tmp_path).crm_snapshot()
    assert snapshot["active"] == 2
    assert snapshot["awaiting"] == 1
    assert snapshot["in_transit"] == 1
    assert snapshot["delivered"] == 1
    assert snapshot["open_tasks"] == 1
    assert snapshot["pipeline_amount"] == 3500
    assert "customer_phone" not in snapshot["sales"][0]
    assert "recipient" not in snapshot["sales"][0]
