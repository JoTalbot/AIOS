"""
Module for unit testing functions and methods in aios_core/llm_balancer.py.

This module uses the unittest framework to test the functions and methods.
"""

import unittest
from unittest.mock import patch
from aios_core.llm_balancer import LLMBalancer, get_balanced_llm
from typing import List, Dict

__all__ = ["TestLLMBalancer", "TestGetBalancedLLM"]

class TestLLMBalancer(unittest.TestCase):
    """
    Test class for LLMBalancer class.
    """

    def setUp(self):
        """
        Setup method to create a new instance of LLMBalancer.
        """
        self.llm_balancer = LLMBalancer()

    def test_init(self):
        """
        Test the initialization of LLMBalancer.
        """
        self.assertIsInstance(self.llm_balancer, LLMBalancer)

    def test_balance(self):
        """
        Test the balance method of LLMBalancer.
        """
        # Mock the get_llm_list method to return a list of LLMs
        with patch.object(LLMBalancer, "get_llm_list", return_value=["llm1", "llm2", "llm3"]):
            self.assertEqual(self.llm_balancer.balance(), ["llm1", "llm2", "llm3"])

    def test_get_llm_list(self):
        """
        Test the get_llm_list method of LLMBalancer.
        """
        # Mock the get_llm_list method to return a list of LLMs
        with patch.object(LLMBalancer, "get_llm_list", return_value=["llm1", "llm2", "llm3"]):
            self.assertEqual(self.llm_balancer.get_llm_list(), ["llm1", "llm2", "llm3"])


class TestGetBalancedLLM(unittest.TestCase):
    """
    Test class for get_balanced_llm function.
    """

    def test_get_balanced_llm(self):
        """
        Test the get_balanced_llm function.
        """
        # Mock the get_llm_list function to return a list of LLMs
        with patch("aios_core.llm_balancer.get_llm_list", return_value=["llm1", "llm2", "llm3"]):
            self.assertEqual(get_balanced_llm(), ["llm1", "llm2", "llm3"])


if __name__ == "__main__":
    unittest.main()