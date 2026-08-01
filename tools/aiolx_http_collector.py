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

    def test_parse_response(self):
        """
        Test the correctness of parsing the HTTP server response.
        Verifies that the parsing result matches the expected data structure.
        """
        test_cases = [
            {
                'name': 'success_response',
                'status_code': 200,
                'json_data': {'data': [1, 2, 3], 'status': 'ok'},
                'expected': {'data': [1, 2, 3], 'status': 'ok'}
            },
            {
                'name': 'empty_response',
                'status_code': 200,
                'json_data': {},
                'expected': {}
            },
            {
                'name': 'string_response',
                'status_code': 200,
                'json_data': {'message': 'hello'},
                'expected': {'message': 'hello'}
            }
        ]

        for case in test_cases:
            with self.subTest(case=case['name']):
                mock_response = unittest.mock.Mock()
                mock_response.status_code = case['status_code']
                mock_response.json.return_value = case['json_data']

                result = self.collector.parse_response(mock_response)
                self.assertEqual(result, case['expected'])

if __name__ == '__main__':
    unittest.main()