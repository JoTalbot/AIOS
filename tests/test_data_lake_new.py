"""data_lake test."""
def test(): from aios_core.data_lake import DataLake; s = DataLake().stats(); assert isinstance(s, dict)
