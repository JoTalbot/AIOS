"""Tests for dispatch history CSV export + endpoint + panel link (v11.9.0)."""

from __future__ import annotations

import csv
import io
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.dashboard import create_dashboard
from aios_core.substrate_convergence import SubstrateConvergenceEngine


@pytest.fixture()
def engine() -> SubstrateConvergenceEngine:
    eng = SubstrateConvergenceEngine()
    eng.execute_substrate_task({"id": "t1", "category": "general", "compute_units": 2})
    eng.execute_substrate_task({"id": 'task,"quoted"', "category": "search", "compute_units": 1})
    return eng


def test_export_header_rows_and_quoting(engine):
    text = engine.export_history_csv()
    lines = text.strip().split("\n")
    assert lines[0] == ",".join(SubstrateConvergenceEngine.HISTORY_CSV_FIELDS)
    assert len(lines) == 1 + 2
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows[0]["task_id"] == "t1"
    assert rows[0]["selected_substrate"] == "silicon_x86_arm"  # general affinity
    assert rows[1]["task_id"] == 'task,"quoted"'  # csv quoting round-trips
    assert rows[1]["selected_substrate"] == "quantum_qpu"  # search affinity
    assert rows[0]["timestamp_iso"].endswith("+00:00")  # UTC ISO8601
    assert float(rows[0]["energy_cost"]) == 0.2  # 2 units * 0.10 silicon


def test_export_limit(engine):
    text = engine.export_history_csv(limit=1)
    rows = list(csv.DictReader(io.StringIO(text)))
    assert len(rows) == 1
    assert rows[0]["task_id"] == 'task,"quoted"'  # newest dispatch wins


def test_export_empty_history():
    text = SubstrateConvergenceEngine().export_history_csv()
    assert text == ",".join(SubstrateConvergenceEngine.HISTORY_CSV_FIELDS) + "\n"


# ----------------------------------------------------------------------
# Dashboard endpoint + panel link
# ----------------------------------------------------------------------


@pytest.fixture()
def client():
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.9.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._substrate_engine = None
    dashboard_module._energy_scheduler = None


def test_export_endpoint_download(client):
    client.post(
        "/api/substrate/schedule", json={"id": "csv-1", "category": "general", "compute_units": 2, "execute": True}
    )
    resp = client.get("/api/substrate/history/export")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert 'attachment; filename="substrate_dispatch_history.csv"' in resp.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    assert len(rows) == 1
    assert rows[0]["task_id"] == "csv-1"

    client.post("/api/substrate/schedule", json={"id": "csv-2", "compute_units": 1, "execute": True})
    resp = client.get("/api/substrate/history/export?limit=1")
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    assert len(rows) == 1
    assert rows[0]["task_id"] == "csv-2"


def test_export_endpoint_empty(client):
    resp = client.get("/api/substrate/history/export")
    assert resp.status_code == 200
    assert resp.text.strip() == ",".join(SubstrateConvergenceEngine.HISTORY_CSV_FIELDS)


def test_substrate_page_has_export_link(client):
    resp = client.get("/substrate")
    assert 'href="/api/substrate/history/export"' in resp.text
    assert "Export CSV" in resp.text
