"""Data ops full scenario."""
from aios_core.storage import Database
from aios_core.data_export import DataExporter
from aios_core.backup_manager import BackupManager
from aios_core.memory_manager import MemoryManager
from aios_core.knowledge_graph import KnowledgeGraph
def test_data_ops():
    db = Database(":memory:")
    assert db.stats()["dialect"] == "sqlite"
    assert DataExporter(":memory:") is not None
    assert BackupManager(":memory:", backup_dir="/tmp/b1").health_report() is not None
    assert MemoryManager().stats() is not None
    assert KnowledgeGraph().stats() is not None
