import pytest
import os
import shutil
from aios_core.rag.vector_store import VectorStore

@pytest.fixture(autouse=True)
def cleanup():
    yield
    if os.path.exists("./data/chroma_db"):
        shutil.rmtree("./data/chroma_db")

def test_add_document():
    store = VectorStore()
    store.add_document("doc1", "Test document", {"source": "test"})
    results = store.search("Test", n_results=1)
    assert len(results) == 1
    assert results[0]["id"] == "doc1"

def test_search_empty():
    store = VectorStore()
    results = store.search("nonexistent", n_results=5)
    assert len(results) == 0

def test_search_multiple():
    store = VectorStore()
    store.add_document("doc1", "Python programming", {"source": "tech"})
    store.add_document("doc2", "Java development", {"source": "tech"})
    store.add_document("doc3", "Cooking recipes", {"source": "food"})
    results = store.search("programming", n_results=2)
    assert len(results) == 2
