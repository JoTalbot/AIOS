"""Master Registry for Universal Execution Adapters in AIOS v16.0.0.

Manages all platform adapters: Android, API, Web, IoT, ARM, Router, Quantum, and Blockchain.
"""

from __future__ import annotations

import time
from typing import Any

from .api_adapter import APIAdapter
from .arm_adapter import ARMEmbeddedAdapter
from .blockchain_adapter import BlockchainNodeAdapter
from .iot_adapter import IoTAdapter
from .quantum_adapter import QuantumAdapter
from .router_adapter import RouterNetworkAdapter
from .web_adapter import WebAdapter


class UniversalAdapterRegistry:
    """Master registry managing all platform execution adapters."""

    def __init__(self) -> None:
        self.api_adapter = APIAdapter()
        self.web_adapter = WebAdapter()
        self.iot_adapter = IoTAdapter()
        self.arm_adapter = ARMEmbeddedAdapter()
        self.router_adapter = RouterNetworkAdapter()
        self.quantum_adapter = QuantumAdapter()
        self.blockchain_adapter = BlockchainNodeAdapter()
        self.execution_log: list[dict[str, Any]] = []

    def execute_platform_action(
        self,
        platform_type: str,
        action: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Dispatch action to appropriate platform adapter."""
        plat = platform_type.lower()

        if plat in ("api", "rest", "graphql", "grpc", "websocket"):
            res = self.api_adapter.execute_api_call(
                protocol=plat,
                endpoint=params.get("endpoint", "/"),
                method=params.get("method", "GET"),
                payload=params.get("payload"),
            )
        elif plat in ("web", "website", "dom", "browser"):
            res = self.web_adapter.execute_web_action(
                url=params.get("url", "http://localhost"),
                action=action,
                selector=params.get("selector", ""),
                text=params.get("text", ""),
            )
        elif plat in ("iot", "mqtt", "coap", "modbus", "zigbee"):
            res = self.iot_adapter.execute_iot_command(
                protocol=plat,
                device_topic=params.get("device_topic", "sensors/temp"),
                command=action,
                payload=params.get("payload"),
            )
        elif plat in ("arm", "gpio", "i2c", "spi", "uart", "raspberry_pi"):
            res = self.arm_adapter.execute_arm_command(
                interface=plat,
                pin_or_address=params.get("pin_or_address", 1),
                mode=params.get("mode", "read"),
                value=params.get("value", 0),
            )
        elif plat in ("router", "openwrt", "ssh", "snmp", "netconf"):
            res = self.router_adapter.execute_router_command(
                protocol=plat,
                router_host=params.get("router_host", "192.168.1.1"),
                command=params.get("command", action),
            )
        elif plat in ("quantum", "qiskit", "cirq", "qasm"):
            res = self.quantum_adapter.execute_quantum_circuit(
                circuit_qasm=params.get("circuit_qasm", "OPENQASM 2.0;"),
                shots=params.get("shots", 1000),
            )
        elif plat in ("blockchain", "evm", "web3", "solana"):
            res = self.blockchain_adapter.execute_smart_contract(
                network=params.get("network", "ethereum"),
                contract_address=params.get("contract_address", "0x123"),
                method=action,
                params=params.get("contract_params", []),
            )
        else:
            res = {
                "platform": plat,
                "action": action,
                "status": "simulated",
                "params": params,
                "timestamp": time.time(),
            }

        self.execution_log.append(res)
        return res

    def registry_stats(self) -> dict[str, Any]:
        """Return total executions per adapter type."""
        return {
            "total_executions": len(self.execution_log),
            "api_calls": len(self.api_adapter.execution_history),
            "web_actions": len(self.web_adapter.execution_history),
            "iot_commands": len(self.iot_adapter.execution_history),
            "arm_commands": len(self.arm_adapter.execution_history),
            "router_commands": len(self.router_adapter.execution_history),
            "quantum_circuits": len(self.quantum_adapter.execution_history),
            "blockchain_transactions": len(self.blockchain_adapter.execution_history),
        }


adapter_registry = UniversalAdapterRegistry()
