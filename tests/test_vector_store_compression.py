import pytest
from aios_core.vector_store import VectorStore, VectorCompressor

def test_vector_compressor():
    comp = VectorCompressor(bits_per_sub=8)
    vec = [0.1, 0.5, 0.9]
    res = comp.compress(vec)
    
    assert res["min"] == 0.1
    assert res["max"] == 0.9
    assert len(res["codes"]) == 3
    
    decomp = comp.decompress(res)
    assert len(decomp) == 3
    # Approximate recovery within PQ precision bounds
    assert abs(decomp[0] - 0.1) < 0.05
    assert abs(decomp[2] - 0.9) < 0.05

def test_vector_store_compression_flow():
    # Regular uncompressed
    store = VectorStore(use_compression=False)
    store.add("vec1", [0.1, 0.2, 0.3], {"label": "test1"})
    store.add("vec2", [0.9, 0.8, 0.7], {"label": "test2"})
    
    assert store.count() == 2
    assert store.stats()["compression_enabled"] is False
    
    # Trigger optimization
    opt_res = store.optimize_memory()
    assert opt_res["status"] == "compressed"
    assert opt_res["converted"] == 2
    assert store.use_compression is True
    
    # Ensure search still works via decompression
    results = store.search([0.9, 0.8, 0.7], top_k=1)
    assert len(results) == 1
    assert results[0]["id"] == "vec2"
    assert results[0]["score"] > 0.95  # Cosine sim should remain high despite PQ approximation
    
    # Add new directly into compressed store
    store.add("vec3", [0.0, 0.0, 0.1])
    assert store.count() == 3
