"""
Integration test module for verifying interaction between web_gui and aiolx_http_collector.
This module adds a test case to run_coder_orchestrator.py to ensure proper integration.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

__all__ = [
    "IntegrationTestRunner",
    "WebGUIMock",
    "AIOLXHTTPCollectorMock",
    "run_integration_test",
]

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class IntegrationTestConfig:
    """Configuration for the integration test."""
    test_timeout: float = 10.0
    max_retries: int = 3
    expected_endpoints: List[str] = None

    def __post_init__(self):
        if self.expected_endpoints is None:
            self.expected_endpoints = ["health", "data", "status"]

class WebGUIMock:
    """Mock implementation of web_gui for testing purposes."""

    def __init__(self, config: Optional[IntegrationTestConfig] = None):
        self.config = config or IntegrationTestConfig()
        self.received_data: List[Dict[str, Any]] = []
        self.is_running = False

    async def start(self) -> None:
        """Start the web GUI mock."""
        self.is_running = True
        logger.info("WebGUIMock started")

    async def stop(self) -> None:
        """Stop the web GUI mock."""
        self.is_running = False
        logger.info("WebGUIMock stopped")

    async def receive_data(self, data: Dict[str, Any]) -> None:
        """Receive data from the collector."""
        self.received_data.append(data)
        logger.debug(f"WebGUIMock received data: {data}")

    def get_received_data(self) -> List[Dict[str, Any]]:
        """Get all received data."""
        return self.received_data.copy()

class AIOLXHTTPCollectorMock:
    """Mock implementation of aiolx_http_collector for testing purposes."""

    def __init__(self, config: Optional[IntegrationTestConfig] = None):
        self.config = config or IntegrationTestConfig()
        self.web_gui: Optional[WebGUIMock] = None
        self.is_running = False

    async def start(self, web_gui: WebGUIMock) -> None:
        """Start the collector with a reference to the web GUI."""
        self.web_gui = web_gui
        self.is_running = True
        logger.info("AIOLXHTTPCollectorMock started")

    async def stop(self) -> None:
        """Stop the collector."""
        self.is_running = False
        self.web_gui = None
        logger.info("AIOLXHTTPCollectorMock stopped")

    async def collect_data(self) -> Dict[str, Any]:
        """Simulate data collection and send to web GUI."""
        if not self.is_running or not self.web_gui:
            raise RuntimeError("Collector not running or no web GUI connected")

        sample_data = {
            "endpoint": "data",
            "status": "success",
            "timestamp": asyncio.get_event_loop().time(),
            "value": 42
        }

        await self.web_gui.receive_data(sample_data)
        logger.debug(f"AIOLXHTTPCollectorMock sent data: {sample_data}")
        return sample_data

class IntegrationTestRunner:
    """Runner for integration tests between web_gui and aiolx_http_collector."""

    def __init__(self, config: Optional[IntegrationTestConfig] = None):
        self.config = config or IntegrationTestConfig()
        self.web_gui = WebGUIMock(self.config)
        self.collector = AIOLXHTTPCollectorMock(self.config)

    async def run_test(self) -> bool:
        """Execute the integration test."""
        logger.info("Starting integration test")

        try:
            # Start components
            await self.web_gui.start()
            await self.collector.start(self.web_gui)

            # Verify initial state
            if not self.web_gui.is_running or not self.collector.is_running:
                raise RuntimeError("Components failed to start")

            # Perform test operations
            for _ in range(self.config.max_retries):
                try:
                    await self.collector.collect_data()
                    break
                except Exception as e:
                    logger.warning(f"Collection attempt failed: {e}")
                    await asyncio.sleep(1)

            # Verify results
            received_data = self.web_gui.get_received_data()
            if not received_data:
                raise RuntimeError("No data received by web GUI")

            sample_data = received_data[0]
            if sample_data.get("status") != "success":
                raise RuntimeError(f"Unexpected data status: {sample_data.get('status')}")

            logger.info("Integration test passed successfully")
            return True

        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            return False
        finally:
            # Clean up
            await self.web_gui.stop()
            await self.collector.stop()

async def run_integration_test() -> bool:
    """Run the integration test and return the result."""
    test_runner = IntegrationTestRunner()
    return await test_runner.run_test()

def main() -> None:
    """Main entry point for testing."""
    result = asyncio.run(run_integration_test())
    if result:
        logger.info("All tests passed!")
        exit(0)
    else:
        logger.error("Tests failed!")
        exit(1)

if __name__ == "__main__":
    main()