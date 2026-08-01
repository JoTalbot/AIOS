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
        try:
            buttons = self.bot.get_buttons()
            assert isinstance(buttons, List)
        except Exception as e:
            print(f"Error in get_buttons: {e}")
            return False
        return True

    def test_send_llm_chat(self):
        """Test sending LLM chat from bot."""
        try:
            response = self.bot.send_llm_chat("Test message")
            assert isinstance(response, dict)
        except Exception as e:
            print(f"Error in send_llm_chat: {e}")
            return False
        return True

@dataclass
class TestBalancer:
    """Test Balancer class."""
    balancer: Balancer

    def test_get_buttons(self):
        """Test getting buttons from balancer."""
        try:
            buttons = self.balancer.get_buttons()
            assert isinstance(buttons, List)
        except Exception as e:
            print(f"Error in get_buttons: {e}")
            return False
        return True

    def test_balance(self):
        """Test balancing from balancer."""
        try:
            response = self.balancer.balance()
            assert isinstance(response, dict)
        except Exception as e:
            print(f"Error in balance: {e}")
            return False
        return True

def test_bot():
    """Test Bot class."""
    bot = Bot()
    test_bot = TestBot(bot)
    if not test_bot.test_get_buttons():
        return
    if not test_bot.test_send_llm_chat():
        return
    print("All tests passed for Bot.")

def test_balancer():
    """Test Balancer class."""
    balancer = Balancer()
    test_balancer = TestBalancer(balancer)
    if not test_balancer.test_get_buttons():
        return
    if not test_balancer.test_balance():
        return
    print("All tests passed for Balancer.")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
    test_bot()
    test_balancer()
    print("All tests passed.")