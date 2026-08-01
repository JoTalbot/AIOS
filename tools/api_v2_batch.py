"""
Integration tests for API v2 batch module.
"""

import pytest
from dataclasses import dataclass
from typing import List
from tools.api_v2_batch import Bot, Balancer

@dataclass
class TestBot:
    """Test Bot class."""
    bot: Bot

    def test_get_buttons(self):
        """Test getting buttons from bot."""
        buttons = self.bot.get_buttons()
        assert isinstance(buttons, List)

    def test_send_llm_chat(self):
        """Test sending LLM chat from bot."""
        response = self.bot.send_llm_chat("Test message")
        assert isinstance(response, dict)

@dataclass
class TestBalancer:
    """Test Balancer class."""
    balancer: Balancer

    def test_get_buttons(self):
        """Test getting buttons from balancer."""
        buttons = self.balancer.get_buttons()
        assert isinstance(buttons, List)

    def test_balance(self):
        """Test balancing from balancer."""
        response = self.balancer.balance()
        assert isinstance(response, dict)

def test_bot():
    """Test Bot class."""
    bot = Bot()
    test_bot = TestBot(bot)
    test_bot.test_get_buttons()
    test_bot.test_send_llm_chat()

def test_balancer():
    """Test Balancer class."""
    balancer = Balancer()
    test_balancer = TestBalancer(balancer)
    test_balancer.test_get_buttons()
    test_balancer.test_balance()

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
    test_bot()
    test_balancer()
    print("All tests passed.")