"""
Module for unit testing aios_core/llm_balancer.py.

This module contains unit tests for the functions in aios_core/llm_balancer.py.
"""

import unittest
from unittest.mock import Mock
from aios_core.llm_balancer import llm_balancer

__all__ = ['TestLlmBalancer']

class TestLlmBalancer(unittest.TestCase):
    """
    Unit tests for llm_balancer module.
    """

    def test_get_balanced_response(self):
        """
        Test get_balanced_response function.
        """
        # Mock input data
        input_data = {'model1': Mock(), 'model2': Mock()}
        # Mock expected output
        expected_output = {'model1': Mock(), 'model2': Mock()}
        # Test function
        result = llm_balancer.get_balanced_response(input_data)
        self.assertEqual(result, expected_output)

    def test_get_balanced_response_with_context(self):
        """
        Test get_balanced_response_with_context function.
        """
        # Mock input data
        input_data = {'model1': Mock(), 'model2': Mock()}
        context = {'key': 'value'}
        # Mock expected output
        expected_output = {'model1': Mock(), 'model2': Mock()}
        # Test function
        result = llm_balancer.get_balanced_response_with_context(input_data, context)
        self.assertEqual(result, expected_output)

if __name__ == '__main__':
    unittest.main()