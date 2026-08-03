"""Тесты безопасной CRM-синхронизации продаж."""
from __future__ import annotations

import json


def test_crm_sync_groups_sales_and_masks_phone(tmp_path):
    from aios_core.crm import CRMStore

    data = tmp_path / "data"
    data.mkdir()
    (data / "sales_lifecycle.json").write_text(json.dumps([
        {"id": "a", "platform": "olx", "chat": "buyer", "recipient": "Client", "customer_phone": "+380501234567",
         "status": "in_transit", "amount": 1200, "item": "Фара", "updated_at": "2026-08-01T10:00:00+00:00"},
        {"id": "b", "platform": "olx", "chat": "buyer", "recipient": "Client", "customer_phone": "+380501234567",
         "status": "delivered", "amount": 1200, "item": "Фара", "updated_at": "2026-08-02T10:00:00+00:00"},
    ]), encoding="utf-8")
    store = CRMStore(tmp_path)
    result = store.sync()
    assert result["count"] == 1
    customer = result["customers"][0]
    assert customer["phone_masked"] == "••••4567"
    assert customer["sales_count"] == 2
    assert customer["delivered_count"] == 1
    assert customer["active_count"] == 1
    assert customer["lifetime_amount"] == 1200
    assert "покупатель" in customer["tags"]
    assert "активная сделка" in customer["tags"]


def test_crm_manual_tag_survives_resync(tmp_path):
    from aios_core.crm import CRMStore

    data = tmp_path / "data"
    data.mkdir()
    (data / "sales_lifecycle.json").write_text(json.dumps([
        {"id": "a", "platform": "olx", "chat": "buyer", "recipient": "Client", "status": "delivered",
         "amount": 500, "item": "Зеркало", "updated_at": "2026-08-01T10:00:00+00:00"},
    ]), encoding="utf-8")
    store = CRMStore(tmp_path)
    customer = store.sync()["customers"][0]
    store.add_tag(customer["id"], "VIP", "Постоянный клиент")
    refreshed = store.sync()["customers"][0]
    assert "VIP" in refreshed["tags"]
    assert refreshed["note"] == "Постоянный клиент"
