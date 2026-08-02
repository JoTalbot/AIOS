import unittest
from aios_core.finetune_dataset import generate_dataset
from aios_core.finetune_dataset import FinetuneDataset

class TestFinetuneDataset(unittest.TestCase):

    def setUp(self):
        self.dataset = FinetuneDataset()

    def test_generate_dataset_default_output_path(self):
        """Test generate_dataset with default output path."""
        result = generate_dataset(self.dataset)
        self.assertIsInstance(result, dict)

    def test_generate_dataset_custom_output_path(self):
        """Test generate_dataset with a custom output path."""
        output_path = "test_data.jsonl"
        result = generate_dataset(self.dataset, output_path=output_path)
        self.assertIsInstance(result, dict)

    def test_generate_dataset_min_examples(self):
        """Test generate_dataset with a minimum number of examples."""
        min_examples = 10
        result = generate_dataset(self.dataset, min_examples=min_examples)
        self.assertIsInstance(result, dict)

    def test_generate_dataset_deduplication(self):
        """Test that generate_dataset deduplicates entries."""
        # Create a dataset with duplicate entries
        data1 = {"instruction": "Test instruction", "input": "Test input"}
        data2 = {"instruction": "Test instruction", "input": "Test input"}
        
        # Mock the collect methods to return the duplicate data
        def mock_collect_from_git():
            return [data1]
        def mock_collect_from_backlog():
            return [data2]
        def mock_collect_from_v3_memory():
            return []
        def mock_collect_from_codebase():
            return []

        # Patch the collect methods
        self.dataset.collect_from_git = mock_collect_from_git
        self.dataset.collect_from_backlog = mock_collect_from_backlog
        self.dataset.collect_from_v3_memory = mock_collect_from_v3_memory
        self.dataset.collect_from_codebase = mock_collect_from_codebase
        
        result = generate_dataset(self.dataset)
        
        # Assert that the result contains only one entry
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], data1)

    def test_generate_dataset_instruction_length_filter(self):
        """Test that generate_dataset filters entries with short instructions."""
        # Create a dataset with a short instruction
        data = {"instruction": "Short", "input": "Test input"}
        
        # Mock the collect methods to return the short instruction data
        def mock_collect_from_git():
            return [data]
        def mock_collect_from_backlog():
            return []
        def mock_collect_from_v3_memory():
            return []
        def mock_collect_from_codebase():
            return []

        # Patch the collect methods
        self.dataset.collect_from_git = mock_collect_from_git
        self.dataset.collect_from_backlog = mock_collect_from_backlog
        self.dataset.collect_from_v3_memory = mock_collect_from_v3_memory
        self.dataset.collect_from_codebase = mock_collect_from_codebase

        result = generate_dataset(self.dataset)
        
        # Assert that the result is empty
        self.assertEqual(len(result), 0)
        
if __name__ == '__main__':
    unittest.main()