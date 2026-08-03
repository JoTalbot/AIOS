"""Тесты CRM-агрегации для Dashboard v3."""
from __future__ import annotations


def test_sales_summary_tracks_pipeline_and_tasks():
    import dashboard_v3 as dash

    sales = [
        {"id": "a", "status": "awaiting_shipment", "amount": 1200},
        {"id": "b", "status": "in_transit", "amount": "800"},
        {"id": "c", "status": "delivered", "amount": 500},
        {"id": "d", "status": "returned", "amount": 600},
    ]
    tasks = [{"sale_id": "a", "status": "open"}, {"sale_id": "c", "status": "done"}]
    result = dash._sales_summary(sales, tasks)

    assert result["total"] == 4
    assert result["active"] == 2
    assert result["awaiting"] == 1
    assert result["in_transit"] == 1
    assert result["delivered"] == 1
    assert result["returned"] == 1
    assert result["open_tasks"] == 1
    assert result["pipeline_amount"] == 2000.0
