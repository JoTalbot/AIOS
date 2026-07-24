"""Tests for WebSocket dashboard — event bus and message streaming."""

from __future__ import annotations

import json
import time

from aios_core.ws_dashboard import (
    DashboardEventBus,
    WSMessage,
    WSMessageType,
    create_ws_dashboard_app,
)


def test_ws_message_types():
    """WSMessageType enum has all expected values."""
    types = list(WSMessageType)
    assert len(types) == 6
    assert WSMessageType.PRICE_DROP.value == "price_drop"
    assert WSMessageType.AUTOWATCH_CYCLE.value == "autowatch_cycle"
    assert WSMessageType.CROSS_PLATFORM.value == "cross_platform"
    assert WSMessageType.SYSTEM_STATUS.value == "system_status"
    assert WSMessageType.FAVORITE_ALERT.value == "favorite_alert"
    assert WSMessageType.VECTOR_MATCH.value == "vector_match"


def test_ws_message_to_json():
    """WSMessage serializes to JSON."""
    msg = WSMessage(
        type=WSMessageType.PRICE_DROP,
        payload={"fingerprint": "fp1", "old_price": 1000, "new_price": 800},
        source="fp1",
    )
    text = msg.to_json()
    data = json.loads(text)
    assert data["type"] == "price_drop"
    assert data["payload"]["fingerprint"] == "fp1"
    assert "timestamp" in data


def test_dashboard_event_bus_init():
    """DashboardEventBus initializes with empty client list."""
    bus = DashboardEventBus()
    assert bus.client_count == 0


def test_dashboard_event_bus_emit_price_drop():
    """emit_price_drop creates a PRICE_DROP message."""
    bus = DashboardEventBus()
    msg = bus.emit_price_drop({
        "fingerprint": "fp-iphone15",
        "old_price": 30000,
        "new_price": 28000,
        "drop_pct": 6.67,
    })
    assert msg.type == WSMessageType.PRICE_DROP
    assert msg.payload["fingerprint"] == "fp-iphone15"
    assert msg.source == "fp-iphone15"


def test_dashboard_event_bus_emit_autowatch():
    """emit_autowatch creates an AUTOWATCH_CYCLE message."""
    bus = DashboardEventBus()
    msg = bus.emit_autowatch({
        "platform": "rozetka",
        "price_drop_alerts": [],
        "stagnant": [],
    })
    assert msg.type == WSMessageType.AUTOWATCH_CYCLE
    assert msg.payload["platform"] == "rozetka"
    assert msg.source == "rozetka"


def test_dashboard_event_bus_emit_cross_platform():
    """emit_cross_platform creates a CROSS_PLATFORM message."""
    bus = DashboardEventBus()
    msg = bus.emit_cross_platform({
        "group_id": "cmp_12345",
        "platforms": ["olx", "rozetka"],
        "lowest_price": 28000,
    })
    assert msg.type == WSMessageType.CROSS_PLATFORM
    assert msg.payload["group_id"] == "cmp_12345"
    assert msg.source == "cmp_12345"


def test_dashboard_event_bus_buffer():
    """Event bus maintains a replay buffer."""
    bus = DashboardEventBus(replay_buffer_size=5)
    # Add 7 messages to buffer
    for i in range(7):
        msg = WSMessage(
            type=WSMessageType.SYSTEM_STATUS,
            payload={"iteration": i},
            source="test",
        )
        bus._buffer.append(msg)
        if len(bus._buffer) > bus._buffer_size:
            bus._buffer = bus._buffer[-bus._buffer_size:]

    assert len(bus._buffer) == 5
    # Buffer should contain last 5 messages (iterations 2-6)
    assert bus._buffer[0].payload["iteration"] == 2
    assert bus._buffer[-1].payload["iteration"] == 6


def test_create_ws_dashboard_app():
    """create_ws_dashboard_app creates a Starlette app with WS route."""
    bus = DashboardEventBus()
    app = create_ws_dashboard_app(event_bus=bus)
    assert app is not None
    # Check that the app has the event bus in state
    assert app.state.event_bus is bus
    # Check routes
    routes = app.routes
    assert len(routes) >= 1
    route = routes[0]
    assert route.path == "/ws/dashboard"


def test_create_ws_dashboard_app_default_bus():
    """App creates default event bus if none provided."""
    app = create_ws_dashboard_app()
    assert app.state.event_bus is not None
    assert app.state.event_bus.client_count == 0
