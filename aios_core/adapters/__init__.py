"""Universal Platform Adapters for AIOS v16.0.0."""

from .api_adapter import APIAdapter
from .arm_adapter import ARMEmbeddedAdapter
from .blockchain_adapter import BlockchainNodeAdapter
from .iot_adapter import IoTAdapter
from .quantum_adapter import QuantumAdapter
from .registry import UniversalAdapterRegistry, adapter_registry
from .router_adapter import RouterNetworkAdapter
from .web_adapter import WebAdapter

__all__ = [
    "APIAdapter",
    "ARMEmbeddedAdapter",
    "BlockchainNodeAdapter",
    "IoTAdapter",
    "QuantumAdapter",
    "RouterNetworkAdapter",
    "UniversalAdapterRegistry",
    "WebAdapter",
    "adapter_registry",
]
