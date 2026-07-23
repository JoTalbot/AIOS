"""Parametrized memory CRUD."""
import pytest
from aios_core.memory_manager import MemoryManager

@pytest.mark.parametrize("owner", ["user1", "admin", "system", "bot_42"])
def test_multi_owner(owner):
    mm = MemoryManager()
    mm.store({"data": "test"}, owner)
    assert mm.stats() is not None
