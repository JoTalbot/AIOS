"""Data lake standalone test."""
from aios_core.data_lake import DataLake
def test_init(): s = DataLake().stats(); assert isinstance(s, dict)
