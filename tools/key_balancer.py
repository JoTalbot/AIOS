# conftest.py
import os
import unittest
from unittest.mock import patch
from tools.key_balancer import KeyBalancer

class TestKeyBalancer(unittest.TestCase):
    def setUp(self):
        self.key_balancer = KeyBalancer()

    @patch('tools.key_balancer.time.sleep')
    def test_add_key(self, mock_sleep):
        # Test adding a key with a valid timeout
        self.key_balancer.add_key('key1', 10)
        self.assertIn('key1', self.key_balancer.keys)
        self.assertEqual(self.key_balancer.keys['key1'], 10)

        # Test adding a key with an invalid timeout
        with self.assertRaises(ValueError):
            self.key_balancer.add_key('key2', -5)

        # Test adding a key with a timeout of 0
        with self.assertRaises(ValueError):
            self.key_balancer.add_key('key3', 0)

    @patch('tools.key_balancer.time.sleep')
    def test_remove_key(self, mock_sleep):
        # Test removing a key
        self.key_balancer.add_key('key1', 10)
        self.key_balancer.remove_key('key1')
        self.assertNotIn('key1', self.key_balancer.keys)

    @patch('tools.key_balancer.time.sleep')
    def test_get_key(self, mock_sleep):
        # Test getting a key
        self.key_balancer.add_key('key1', 10)
        self.assertEqual(self.key_balancer.get_key('key1'), 10)

        # Test getting a non-existent key
        self.assertIsNone(self.key_balancer.get_key('key2'))

    @patch('tools.key_balancer.time.sleep')
    def test_update_key(self, mock_sleep):
        # Test updating a key
        self.key_balancer.add_key('key1', 10)
        self.key_balancer.update_key('key1', 20)
        self.assertEqual(self.key_balancer.get_key('key1'), 20)

        # Test updating a non-existent key
        self.key_balancer.update_key('key2', 20)
        self.assertIsNone(self.key_balancer.get_key('key2'))

    def test_get_all_keys(self):
        # Test getting all keys
        self.key_balancer.add_key('key1', 10)
        self.key_balancer.add_key('key2', 20)
        self.assertEqual(self.key_balancer.get_all_keys(), {'key1': 10, 'key2': 20})

    def test_get_all_keys_empty(self):
        # Test getting all keys when there are no keys
        self.assertEqual(self.key_balancer.get_all_keys(), {})

if __name__ == '__main__':
    unittest.main()