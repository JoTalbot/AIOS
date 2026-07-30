"""Unit tests for AIOS v16.0.0 Universal Cross-Platform Execution Adapters."""

from __future__ import annotations

from starlette.testclient import TestClient

from aios_core.adapters import (
    APIAdapter,
    ARMEmbeddedAdapter,
    BlockchainNodeAdapter,
    IoTAdapter,
    QuantumAdapter,
    RouterNetworkAdapter,
    UniversalAdapterRegistry,
    WebAdapter,
)
from aios_core.dashboard import create_dashboard
from aios_core.orchestrator import Orchestrator
from sdk.aios_sdk import AIOSClientSync


def test_api_adapter():
    """Test API adapter execution over REST, GraphQL, gRPC."""
    adapter = APIAdapter()
    res = adapter.execute_api_call("rest", "http://api.example.com/data", "POST", {"key": "value"})
    assert res["status"] == "success"
    assert res["protocol"] == "rest"


def test_web_adapter():
    """Test Web Site / DOM RPA adapter."""
    adapter = WebAdapter()
    res = adapter.execute_web_action("http://example.com", "scrape")
    assert res["status"] == "success"
    assert "Scraped content" in res["extracted_data"]


def test_iot_adapter():
    """Test IoT MQTT and CoAP sensor/actuator adapter."""
    adapter = IoTAdapter()
    res = adapter.execute_iot_command("mqtt", "sensors/temp", "read_sensor")
    assert res["status"] == "success"
    assert "temperature" in res["telemetry"]


def test_arm_adapter():
    """Test ARM Cortex / Raspberry Pi GPIO pin I/O adapter."""
    adapter = ARMEmbeddedAdapter()
    res = adapter.execute_arm_command("gpio", pin_or_address=17, mode="write", value=1)
    assert res["status"] == "success"
    assert res["value"] == 1


def test_router_adapter():
    """Test Router SSH / SNMP network infrastructure adapter."""
    adapter = RouterNetworkAdapter()
    res = adapter.execute_router_command("ssh", "192.168.1.1", "show ip bgp")
    assert res["status"] == "success"
    assert "Executed" in res["output"]


def test_quantum_adapter():
    """Test Quantum circuit Qiskit/QASM simulator adapter."""
    adapter = QuantumAdapter()
    res = adapter.execute_quantum_circuit("OPENQASM 2.0;", shots=500)
    assert res["status"] == "success"
    assert res["shots"] == 500


def test_blockchain_adapter():
    """Test Blockchain & Smart Contract transaction adapter."""
    adapter = BlockchainNodeAdapter()
    res = adapter.execute_smart_contract("ethereum", "0x123", "transfer", [100])
    assert res["status"] == "success"
    assert "transaction_hash" in res


def test_universal_adapter_registry():
    """Test Master Universal Adapter Registry dispatching."""
    reg = UniversalAdapterRegistry()
    res = reg.execute_platform_action("iot", "read", {"device_topic": "home/sensor"})
    assert res["status"] == "success"

    stats = reg.registry_stats()
    assert stats["total_executions"] == 1
    assert stats["iot_commands"] == 1


def test_adapter_rest_api_and_sdk_integration():
    """Test REST API endpoints and SDK methods for platform adapters."""
    orch = Orchestrator()
    app = create_dashboard(orch)
    client = TestClient(app)

    # API /api/adapters/execute
    res1 = client.post(
        "/api/adapters/execute",
        json={"platform_type": "router", "action": "reboot", "params": {"router_host": "10.0.0.1"}},
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "success"

    # API /api/adapters/stats
    res2 = client.get("/api/adapters/stats")
    assert res2.status_code == 200
    assert "total_executions" in res2.json()

    # SDK Sync methods verification
    sdk = AIOSClientSync("http://localhost:8000")
    assert hasattr(sdk, "execute_adapter_action")
    assert hasattr(sdk, "get_adapter_stats")
