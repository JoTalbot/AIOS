"""Data lake full."""
from aios_core.data_lake import DataLake
def test(): s=DataLake().stats(); assert isinstance(s,dict)
