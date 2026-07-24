import pytest
from aios_core.memory_manager import MemoryManager
from aios_core.storage import Database

def test_memory_manager_semantic_search():
    db = Database(":memory:")
    manager = MemoryManager(db=db)
    
    # Store memory with vector embedding
    res1 = manager.store(
        content={"text": "I love quantum physics"},
        category="personal",
        owner_id="user_1",
        metadata={"embedding": [0.9, 0.1, 0.1]}
    )
    
    res2 = manager.store(
        content={"text": "I enjoy baking cookies"},
        category="personal",
        owner_id="user_1",
        metadata={"embedding": [0.1, 0.9, 0.2]}
    )
    
    assert manager.vector_store.count() == 2
    
    # Perform semantic search for physics (vector [1.0, 0.0, 0.0])
    results = manager.semantic_search([1.0, 0.0, 0.0], top_k=1, requester_id="user_1")
    
    assert len(results) == 1
    assert results[0]["id"] == res1["id"]
    assert "similarity_score" in results[0]
