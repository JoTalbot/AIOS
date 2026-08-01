"""
Module for testing aiolx_http_collector.py.
"""

import unittest
from unittest.mock import patch
from tools.aiolx_http_collector import AiolxHttpCollector

__all__ = ['AiolxHttpCollectorTest']

class AiolxHttpCollectorTest(unittest.TestCase):
    """
    Test class for AiolxHttpCollector.
    """

    def setUp(self):
        """
        Set up test environment.
        """
        self.collector = AiolxHttpCollector()

    @patch('tools.aiolx_http_collector.requests.get')
    def test_parse_response_success(self, mock_get):
        """
        Test parsing response with success status code.
        """
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {'key': 'value'}
        result = self.collector.parse_response(mock_response)
        self.assertEqual(result, {'key': 'value'})

    @patch('tools.aiolx_http_collector.requests.get')
    def test_parse_response_error(self, mock_get):
        """
        Test parsing response with error status code.
        """
        mock_response = mock_get.return_value
        mock_response.status_code = 404
        with self.assertRaises(ValueError):
            self.collector.parse_response(mock_response)

    @patch('tools.aiolx_http_collector.requests.get')
    def test_parse_response_invalid_json(self, mock_get):
        """
        Test parsing response with invalid JSON.
        """
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = None
        with self.assertRaises(ValueError):
            self.collector.parse_response(mock_response)

    def test_handle_error(self):
        """
        Test handling error.
        """
        error = ValueError('Test error')
        result = self.collector.handle_error(error)
        self.assertEqual(result, str(error))

if __name__ == '__main__':
    unittest.main()