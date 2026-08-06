"""No-action workflow readiness uses only calibration metadata."""
from __future__ import annotations

import json


def test_readiness_requires_all_selectors(tmp_path):
    from aios_core.phone_workflow_readiness import PhoneWorkflowReadiness

    data = tmp_path / "data" / "android_gateway"
    data.mkdir(parents=True)
    (data / "app_ui_calibrations.json").write_text(json.dumps({
        "whatsapp": {"selectors": {"chat_search": True}},
        "ime": {"selectors": {"chat_search": True}},
        "uklon": {"selectors": {"pickup_address": True, "destination_address": False}},
        "easyway": {"selectors": {"destination_trigger": True}},
    }), encoding="utf-8")
    report = PhoneWorkflowReadiness(tmp_path).snapshot()
    rows = {row["id"]: row for row in report["workflows"]}
    assert rows["whatsapp"]["ready"] is True
    assert rows["uklon"]["ready"] is False
    assert report["ready"] == 3


def test_uklon_extended_readiness_requires_explicit_capabilities(tmp_path):
    from aios_core.phone_workflow_readiness import PhoneWorkflowReadiness

    data = tmp_path / "data" / "android_gateway"
    data.mkdir(parents=True)
    (data / "app_ui_calibrations.json").write_text(json.dumps({
        "uklon": {
            "selectors": {"pickup_address": True, "destination_address": True},
            "capabilities": {
                "alternate_pickup": True,
                "multi_stop_add": True,
                "multi_stop_delete": True,
                "multi_stop_reorder": False,
            },
        },
    }), encoding="utf-8")
    row = PhoneWorkflowReadiness(tmp_path).snapshot()["workflows"][2]
    assert row["ready"] is True
    assert row["extended_ready"] is False
    assert row["extended_available"] == 3
