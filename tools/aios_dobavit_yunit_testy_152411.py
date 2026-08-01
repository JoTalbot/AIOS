"""
Unit tests for aios_core/llm_balancer.py
"""

import asyncio
import unittest
from unittest.mock import MagicMock
from aios_core.llm_balancer import LLMBalancer

class TestLLMBalancer(unittest.IsolatedAsyncioTestCase):
    async def test_load_key(self):
        """Test load_key function"""
        balancer = LLMBalancer()
        key = "test_key"
        balancer.load_key(key)
        self.assertEqual(balancer.key, key)

    async def test_balance(self):
        """Test balance function"""
        balancer = LLMBalancer()
        # Mock LLM instances
        llm1 = MagicMock()
        llm2 = MagicMock()
        llm3 = MagicMock()
        balancer.llms = [llm1, llm2, llm3]
        # Test balance with even number of LLMs
        await balancer.balance()
        self.assertEqual(balancer.current_llm, llm1)
        # Test balance with odd number of LLMs
        balancer.llms = [llm1, llm2]
        await balancer.balance()
        self.assertEqual(balancer.current_llm, llm1)

    async def test_timeout(self):
        """Test timeout function"""
        balancer = LLMBalancer()
        # Mock timeout
        balancer.timeout = 1
        # Test timeout with no timeout
        await asyncio.sleep(0.5)
        self.assertTrue(balancer.timeout_expired)
        # Test timeout with timeout
        await asyncio.sleep(1.5)
        self.assertTrue(balancer.timeout_expired)

if __name__ == '__main__':
    unittest.main()

__all__ = ['TestLLMBalancer']