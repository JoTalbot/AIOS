"""Тесты бизнес-цикла продажи: ТТН → резерв → отправка → доставка/возврат."""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import run_inventory
from aios_core.sales_lifecycle import SalesLifecycle, _now


def _prepare_root(tmp_path: Path, items: list[dict] | None = None) -> SalesLifecycle:
    data = tmp_path / "data"
    data.mkdir(parents=True)
    (data / "inventory.json").write_text(json.dumps(items or [
        {"name": "Фара BMW X5", "qty": 1, "price": 2500, "category": "оптика"},
    ], ensure_ascii=False), encoding="utf-8")
    return SalesLifecycle(tmp_path)


def _inventory(root: Path) -> list[dict]:
    return json.loads((root / "data" / "inventory.json").read_text(encoding="utf-8"))


def test_ttn_reserves_then_ships_and_closes_sale(tmp_path):
    lifecycle = _prepare_root(tmp_path)

    created = lifecycle.register_ttn(
        ttn="20451502718405", item="Фара BMW X5", amount="2500",
        recipient="Тестовий Покупець", phone="0670000000", city="Київ", warehouse="Відділення №1",
    )
    assert created["status"] == "ok"
    assert created["sale"]["status"] == "awaiting_shipment"
    assert len(lifecycle.list_open_tasks()) == 1

    item = _inventory(tmp_path)[0]
    assert item["qty"] == 1              # физически ещё на складе
    assert item["sale_state"] == "sold_awaiting_shipment"
    assert run_inventory.reserved_qty(item) == 1
    assert run_inventory.available_qty(item) == 0  # повторно не продадим

    # Повтор API/ретрай не создаёт второй резерв и вторую задачу.
    same = lifecycle.register_ttn(
        ttn="20451502718405", item="Фара BMW X5", amount=2500,
        recipient="Тестовий Покупець", phone="0670000000", city="Київ", warehouse="Відділення №1",
    )
    assert same["status"] == "ok"
    assert same["created"] is False
    assert len(lifecycle.list_open_tasks()) == 1
    assert len(_inventory(tmp_path)[0]["reservations"]) == 1

    sent = lifecycle.mark_shipped("20451502718405")
    assert sent["status"] == "ok"
    assert sent["sale"]["status"] == "in_transit"
    item = _inventory(tmp_path)[0]
    assert item["qty"] == 0
    assert run_inventory.reserved_qty(item) == 0
    assert lifecycle.list_open_tasks() == []

    delivered = lifecycle.mark_delivered("20451502718405")
    assert delivered["status"] == "ok"
    assert delivered["sale"]["status"] == "delivered"
    finance = json.loads((tmp_path / "data" / "finance.json").read_text(encoding="utf-8"))
    assert len(finance) == 1
    assert finance[0]["kind"] == "sale"
    assert finance[0]["amount"] == 2500.0

    # Повторное сообщение о доставке не дублирует финансовую запись.
    repeat = lifecycle.mark_delivered("20451502718405")
    assert repeat["status"] == "ok"
    finance_after = json.loads((tmp_path / "data" / "finance.json").read_text(encoding="utf-8"))
    assert len(finance_after) == 1


def test_return_waits_for_physical_receipt_before_restock(tmp_path):
    lifecycle = _prepare_root(tmp_path)
    lifecycle.register_ttn(ttn="20451502718406", item="Фара BMW X5", amount=2500,
                           recipient="Клієнт", phone="0670000000", city="Львів", warehouse="№2")
    lifecycle.mark_shipped("20451502718406")

    returned = lifecycle.mark_returned("20451502718406")
    assert returned["status"] == "ok"
    assert returned["sale"]["status"] == "returned"
    assert _inventory(tmp_path)[0]["qty"] == 0  # ТТН «возвращена» не равна физическому приёму
    tasks = lifecycle.list_open_tasks()
    assert len(tasks) == 1
    assert tasks[0]["task"]["kind"] == "return_receive"

    accepted = lifecycle.mark_return_received("20451502718406")
    assert accepted["status"] == "ok"
    assert accepted["sale"]["status"] == "return_received"
    assert _inventory(tmp_path)[0]["qty"] == 1
    assert lifecycle.list_open_tasks() == []
    assert not (tmp_path / "data" / "finance.json").exists()


def test_tracking_moves_sale_and_reminders_are_deduplicated(tmp_path):
    lifecycle = _prepare_root(tmp_path)
    lifecycle.register_ttn(ttn="20451502718407", item="Фара BMW X5", amount=2500,
                           recipient="Клієнт", phone="0670000000", city="Одеса", warehouse="№3")

    reminders = lifecycle.due_notifications(_now() + timedelta(hours=3))
    assert len(reminders) == 1
    assert "отправьте" in reminders[0]["text"].lower()
    # Следующий вызов в ту же секунду не должен повторно отправить уведомление.
    assert lifecycle.due_notifications(_now() + timedelta(hours=3)) == []

    in_transit = lifecycle.apply_tracking("20451502718407", "Відправлення прийнято та прямує до отримувача")
    assert in_transit["phase"] == "in_transit"
    assert any("перевозчик принял" in text for text in in_transit["notifications"])
    assert _inventory(tmp_path)[0]["qty"] == 0

    delivered = lifecycle.apply_tracking("20451502718407", "Відправлення отримано")
    assert delivered["phase"] == "delivered"
    assert any("Сделка закрыта" in text for text in delivered["notifications"])
    assert lifecycle.active_tracking_sales() == []


def test_ttn_deactivates_only_matched_olx_ad_when_stock_is_exhausted(tmp_path, monkeypatch):
    lifecycle = _prepare_root(tmp_path)
    (tmp_path / "data" / "olx_published.json").write_text(json.dumps([
        {"title": "Фара BMW X5 оригінал", "ad_id": "ad-123", "url": "https://example.test/ad-123"},
    ], ensure_ascii=False), encoding="utf-8")
    calls = []

    def fake_delete(self, ad_id):
        calls.append(ad_id)
        return {"status": "deactivated", "ad_id": ad_id, "adapter_status": "deactivated"}

    monkeypatch.setattr(SalesLifecycle, "_run_olx_deactivate", fake_delete)
    result = lifecycle.register_ttn(ttn="20451502718410", item="Фара BMW X5", amount=2500,
                                    recipient="Клієнт", phone="0670000000", city="Київ", warehouse="№1")
    assert calls == ["ad-123"]
    assert result["olx"]["status"] == "deactivated"
    journal = json.loads((tmp_path / "data" / "olx_published.json").read_text(encoding="utf-8"))
    assert journal[0]["active"] is False
    assert journal[0]["status"] == "deactivated"

    # При остатке из двух одинаковых деталей одна продажа не должна скрывать
    # объявление: оно всё ещё честно предлагает доступную вторую деталь.
    another = _prepare_root(tmp_path / "two", [{"name": "Фара BMW X5", "qty": 2, "price": 2500}])
    (tmp_path / "two" / "data" / "olx_published.json").write_text(json.dumps([
        {"title": "Фара BMW X5 оригінал", "ad_id": "ad-456"},
    ], ensure_ascii=False), encoding="utf-8")
    second = another.register_ttn(ttn="20451502718411", item="Фара BMW X5", amount=2500,
                                  recipient="Клієнт", phone="0670000001", city="Київ", warehouse="№2")
    assert second["olx"]["status"] == "kept_active"
    assert second["olx"]["available_qty"] == 1
    assert calls == ["ad-123"]


def test_no_reference_requires_clarification_when_multiple_shipments(tmp_path):
    lifecycle = _prepare_root(tmp_path, [
        {"name": "Фара BMW X5", "qty": 1, "price": 2500},
        {"name": "Капот Skoda", "qty": 1, "price": 3500},
    ])
    lifecycle.register_ttn(ttn="20451502718408", item="Фара BMW X5", amount=2500,
                           recipient="Клієнт A", phone="0670000001", city="Київ", warehouse="№1")
    lifecycle.register_ttn(ttn="20451502718409", item="Капот Skoda", amount=3500,
                           recipient="Клієнт Б", phone="0670000002", city="Київ", warehouse="№2")

    result = lifecycle.mark_shipped("")
    assert result["status"] == "ambiguous"
    assert "несколько сделок" in result["message"]
