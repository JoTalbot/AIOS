"""Tests for the orderbook ws collector message parsing."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.collect_orderbook_ws import depth_msg_to_snapshot  # noqa: E402


def test_valid_depth_message_carries_measured_latency():
    msg = {
        "e": "depthUpdate",
        "lastUpdateId": 123,
        "bids": [["100.0", "1.5"], ["99.9", "2.0"]],
        "asks": [["100.1", "1.5"], ["100.2", "2.0"]],
    }
    now_ms = 1786950000230.0
    snap = depth_msg_to_snapshot(msg, now_ms, latency_ms=107.0)
    assert snap is not None
    assert snap["latency_ms"] == 107.0
    assert snap["bid"] == 100.0
    assert snap["ask"] == 100.1
    assert snap["mid"] == pytest.approx(100.05)
    assert snap["spread_bps"] == pytest.approx((0.1 / 100.05) * 1e4)


def test_default_latency_is_zero():
    msg = {
        "lastUpdateId": 123,
        "bids": [["100.0", "1.5"]],
        "asks": [["100.1", "1.5"]],
    }
    snap = depth_msg_to_snapshot(msg, 1786950000230.0)
    assert snap is not None
    assert snap["latency_ms"] == 0.0


def test_garbage_messages_are_none():
    assert depth_msg_to_snapshot({"lastUpdateId": 1, "bids": [], "asks": []}, 1.0) is None
    assert depth_msg_to_snapshot({"lastUpdateId": 1, "bids": [["0", "1"]], "asks": [["1", "1"]]}, 1.0) is None
    assert depth_msg_to_snapshot({"lastUpdateId": 1, "bids": [["100", "1"]], "asks": [["99", "1"]]}, 1.0) is None
