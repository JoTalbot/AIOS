# tools/aios_dobavit_yunit_testy_165155.py

"""
Module for unit tests of aios_core/meta_cognitive_self_coder.py
"""

import unittest
from unittest.mock import patch
from aios_core import meta_cognitive_self_coder  # type: ignore

class TestMetaCognitiveSelfCoder(unittest.IsolatedAsyncioTestCase):
    """
    Test class for MetaCognitiveSelfCoder
    """

    async def test_generate_code(self):
        """
        Test generate_code method
        """
        with patch('builtins.print') as mock_print:
            await meta_cognitive_self_coder.MetaCognitiveSelfCoder().generate_code()
            mock_print.assert_called_once()

    async def test_generate_code_with_args(self):
        """
        Test generate_code method with arguments
        """
        with patch('builtins.print') as mock_print:
            await meta_cognitive_self_coder.MetaCognitiveSelfCoder().generate_code('arg1', 'arg2')
            mock_print.assert_called_once()

    async def test_generate_code_with_invalid_args(self):
        """
        Test generate_code method with invalid arguments
        """
        with self.assertRaises(TypeError):
            await meta_cognitive_self_coder.MetaCognitiveSelfCoder().generate_code('arg1')

    async def test_meta_cognitive_self_coder_init(self):
        """
        Test MetaCognitiveSelfCoder init method
        """
        self.assertIsInstance(meta_cognitive_self_coder.MetaCognitiveSelfCoder(), meta_cognitive_self_coder.MetaCognitiveSelfCoder)

    async def test_meta_cognitive_self_coder_init_with_args(self):
        """
        Test MetaCognitiveSelfCoder init method with arguments
        """
        self.assertIsInstance(meta_cognitive_self_coder.MetaCognitiveSelfCoder('arg1', 'arg2'), meta_cognitive_self_coder.MetaCognitiveSelfCoder)

    async def test_meta_cognitive_self_coder_init_with_invalid_args(self):
        """
        Test MetaCognitiveSelfCoder init method with invalid arguments
        """
        with self.assertRaises(TypeError):
            meta_cognitive_self_coder.MetaCognitiveSelfCoder('arg1')

if __name__ == '__main__':
    unittest.main()