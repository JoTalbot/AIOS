import unittest
from webdav_server import list_files, semantic_search

class TestBatch1(unittest.TestCase):
    def test_list_files(self):
        res = list_files()
        self.assertIsInstance(res, list)

if __name__ == "__main__":
    unittest.main()
