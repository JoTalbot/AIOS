"""migration boundary test."""
from aios_core.migration import MigrationManager

def test_empty(): mm = MigrationManager(':memory:'); assert len(mm.migrations) == 0
