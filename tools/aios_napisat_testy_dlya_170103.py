from dataclasses import dataclass
from typing import List, Dict
import unittest
from unittest.mock import patch
import numpy as np

__all__ = ['Model', 'TestModel']

@dataclass
class Model:
    """Base model class."""
    weights: Dict[str, float]

class TestModel(unittest.TestCase):
    """Test cases for Model class."""

    def test_empty_list(self):
        """Test empty list of models."""
        self.assertEqual(Model(weights={}).weights, {})

    @patch('numpy.random.rand')
    def test_invalid_weights(self, mock_rand):
        """Test invalid weights."""
        mock_rand.return_value = np.array([1.0, 2.0, 3.0])
        with self.assertRaises(ValueError):
            Model(weights={'weight1': 1.0, 'weight2': 2.0, 'weight3': 3.0})

    def test_normal_weights(self):
        """Test normal weights."""
        model = Model(weights={'weight1': 1.0, 'weight2': 2.0})
        self.assertEqual(model.weights, {'weight1': 1.0, 'weight2': 2.0})

    def test_exceptions(self):
        """Test exceptions."""
        with self.assertRaises(TypeError):
            Model(weights='invalid')
        with self.assertRaises(TypeError):
            Model(weights=[1, 2, 3])

if __name__ == '__main__':
    unittest.main()