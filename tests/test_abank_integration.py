"""Core-gate tests for the safe A-Банк integration boundary."""
from __future__ import annotations

import json

import httpx
import pytest


def test_amount_and_csv_parser_handles_ukrainian_notation():
    from aios_core.banking.parsers import parse_amount_minor, parse_csv_statement

    assert parse_amount_minor("1 234,56 грн") == 123456
    assert parse_amount_minor("-123.45 UAH") == -12345
    rows, errors = parse_csv_statement(
        "дата;сума;валюта;призначення\n06.08.2026;-123,45;UAH;Coffee\n07.08.2026;1 000,00;UAH;Salary\n"
    )
    assert not errors
    assert [row.amount_minor for row in rows] == [-12345, 100000]
    assert rows[0].direction == "debit"
    assert rows[1].direction == "credit"


def test_json_import_is_idempotent_and_does_not_store_raw_statement(tmp_path):
    from aios_core.banking import BankingService

    content = json.dumps({"transactions": [{"date": "2026-08-06", "amount": "-10,00", "description": "Coffee"}]})
    service = BankingService(tmp_path)
    first = service.import_content("alice", content, format="json")
    second = service.import_content("alice", content, format="json")
    assert first.imported == 1
    assert second.imported == 0
    assert len(service.list_transactions("alice")) == 1
    stored = next(tmp_path.glob("subject-*.json")).read_text(encoding="utf-8")
    assert "transactions" in stored
    assert "{\"transactions\"" not in stored


def test_scope_boundary_rejects_write_scopes():
    from aios_core.banking import validate_scopes

    assert set(validate_scopes(["accounts:read", "transactions:read"])) == {"accounts:read", "transactions:read"}
    with pytest.raises(ValueError, match="write scopes"):
        validate_scopes(["accounts:read", "payments:write"])


def test_abank_business_signature_matches_documented_hmac_vector():
    from aios_core.banking import ABankBusinessAPI, sign_body

    body = '{"order_id":"123456789"}'
    assert sign_body(body, "secret") == "TXFbtdiTiR/bSbB6b9EVE/bd7lqUGcdTBv6VesoSZYk="
    request = ABankBusinessAPI().build_request("getLoanStatus", {"order_id": "123456789"}, secret="secret")
    assert request.headers["signature"] == request.signature
    assert request.to_dict()["network_sent"] is False


def test_default_open_banking_provider_is_disabled_and_read_only(monkeypatch):
    monkeypatch.delenv("AIOS_ABANK_OPEN_BANKING_ENABLED", raising=False)
    monkeypatch.delenv("AIOS_ABANK_OPEN_BANKING_PROVIDER", raising=False)
    from aios_core.banking import BankingService

    status = BankingService().status("alice")
    assert status["personal_finance"]["status"] == "disabled"
    assert status["personal_finance"]["read_only"] is True
    assert status["automation_policy"]["payments"] is False
    assert status["business_api"]["network_sent"] is False


@pytest.mark.asyncio
async def test_api_auth_owner_isolation_and_manual_import(monkeypatch, tmp_path):
    monkeypatch.setenv("AIOS_BANKING_DATA", str(tmp_path / "banking"))
    from aios_core.api.app import create_app

    app = create_app(
        db_path=":memory:",
        api_keys={
            "viewer-key": {"subject": "alice", "roles": ["viewer"]},
            "writer-key": {"subject": "alice", "roles": ["writer"]},
            "bob-key": {"subject": "bob", "roles": ["viewer"]},
        },
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/api/v1/banking/abank/status")).status_code == 401
        viewer = {"Authorization": "Bearer viewer-key"}
        writer = {"Authorization": "Bearer writer-key"}
        bob = {"Authorization": "Bearer bob-key"}
        status = await client.get("/api/v1/banking/abank/status", headers=viewer)
        assert status.status_code == 200
        assert status.json()["automation_policy"]["payments"] is False
        payload = {
            "format": "csv",
            "account_id": "manual-uah",
            "content": "date,amount,currency,description\n2026-08-06,-25.50,UAH,Coffee\n",
        }
        imported = await client.post("/api/v1/banking/import", json=payload, headers=writer)
        assert imported.status_code == 201
        assert imported.json()["imported"] == 1
        alice_rows = await client.get("/api/v1/banking/transactions", headers=viewer)
        assert alice_rows.status_code == 200
        assert alice_rows.json()["count"] == 1
        bob_rows = await client.get("/api/v1/banking/transactions", headers=bob)
        assert bob_rows.status_code == 200
        assert bob_rows.json()["count"] == 0
        consent = await client.get("/api/v1/banking/consent", headers=viewer)
        assert consent.status_code == 200
        assert consent.json()["read_only"] is True
