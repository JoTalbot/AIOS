"""Tests for aios_core/memory_compression.py and its AgentMemorySystem integration (v11.3.0)."""

from __future__ import annotations

import numpy as np
import pytest

from aios_core.memory_compression import (
    CompressedVector,
    HashingVectorizer,
    VectorCompressor,
    pack_compressed,
    unpack_compressed,
)


class TestHashingVectorizer:
    def test_deterministic(self):
        v = HashingVectorizer(dim=128)
        a = v.vectorize("olx collect success")
        b = v.vectorize("olx collect success")
        assert np.array_equal(a, b)

    def test_shape_and_norm(self):
        v = HashingVectorizer(dim=256)
        vec = v.vectorize("some text to hash into buckets")
        assert vec.shape == (256,)
        assert vec.dtype == np.float64
        assert np.linalg.norm(vec) == pytest.approx(1.0)

    def test_empty_text_zero_vector(self):
        v = HashingVectorizer(dim=64)
        vec = v.vectorize("")
        assert vec.shape == (64,)
        assert np.count_nonzero(vec) == 0

    def test_invalid_dim(self):
        with pytest.raises(ValueError):
            HashingVectorizer(dim=0)


class TestVectorCompressor:
    def test_deterministic_projection(self):
        c1 = VectorCompressor(target_dim=32, seed=7)
        c2 = VectorCompressor(target_dim=32, seed=7)
        vec = np.linspace(0, 1, 100)
        p1 = c1.project(vec)
        p2 = c2.project(vec)
        assert np.allclose(p1, p2)

    def test_compress_shape_payload(self):
        c = VectorCompressor(target_dim=64)
        vec = np.random.default_rng(1).normal(size=512)
        cv = c.compress(vec)
        assert isinstance(cv, CompressedVector)
        assert cv.dims == 64
        assert cv.source_dim == 512
        assert len(cv.payload) == 64
        assert cv.byte_size() == 64 + 16 + 8

    def test_self_similarity_high_after_roundtrip(self):
        c = VectorCompressor(target_dim=64)
        vec = HashingVectorizer(dim=512).vectorize("prom parse success fast selector")
        cv = c.compress(vec)
        assert c.cosine_similarity(cv, cv) == pytest.approx(1.0, abs=1e-9)

    def test_geometry_preserved_related_vs_unrelated(self):
        """Similar texts stay closer than unrelated ones in compressed space."""
        c = VectorCompressor(target_dim=128)
        vec = HashingVectorizer(dim=512)
        v1 = vec.vectorize("olx collect ads success page parsed fully")
        v2 = vec.vectorize("olx collect ads success page parsed partially")
        v3 = vec.vectorize("quantum gravity entanglement manifold topology")
        c1, c2, c3 = c.compress(v1), c.compress(v2), c.compress(v3)
        assert c.cosine_similarity(c1, c2) > c.cosine_similarity(c1, c3)

    def test_top1_recall_preserved(self):
        """Querying with the exact document text must return that document."""
        docs = [
            "olx iphone 15 pro listing price drop",
            "rozetka laptop discount coupon black friday",
            "prom supplier invoice export xml",
            "telegram bot subscription notification",
            "quantum qpu decoherence error mitigation",
            "android emulator adb screenshot capture",
            "user login two factor authentication success",
            "database migration postgresql schema update",
        ]
        vec = HashingVectorizer(dim=512)
        c = VectorCompressor(target_dim=64)
        compressed = [c.compress(vec.vectorize(d)) for d in docs]
        for i, doc in enumerate(docs):
            q = c.compress(vec.vectorize(doc))
            sims = [c.cosine_similarity(q, cv) for cv in compressed]
            assert int(np.argmax(sims)) == i, f"top-1 mismatch for doc {i}: {doc}"

    def test_storage_report_ratio(self):
        c = VectorCompressor(target_dim=64)
        c.fit(512)
        report = c.storage_report()
        assert report["original_bytes"] == 512 * 8
        assert report["compressed_bytes"] == 64 + 16
        assert report["ratio"] > 40  # ~51x

    def test_constant_vector_quantization(self):
        """Degenerate (constant) projected vectors must not divide-by-zero."""
        c = VectorCompressor(target_dim=16)
        cv = c.compress(np.zeros(50))
        assert all(b == 0 for b in cv.payload)
        back = c.decompress(cv)
        assert np.allclose(back, 0.0)

    def test_mismatched_dims_raises(self):
        c = VectorCompressor(target_dim=32)
        other = CompressedVector(dims=64, source_dim=128, vmin=0.0, vmax=1.0, payload=b"\x00" * 64)
        with pytest.raises(ValueError):
            c.decompress(other)

    def test_pack_unpack_roundtrip(self):
        c = VectorCompressor(target_dim=32)
        cv = c.compress(np.arange(100, dtype=np.float64))
        blob = pack_compressed(cv)
        restored = unpack_compressed(blob)
        assert restored.dims == cv.dims
        assert restored.source_dim == cv.source_dim
        assert restored.vmin == cv.vmin
        assert restored.vmax == cv.vmax
        assert restored.payload == cv.payload

    def test_dict_roundtrip(self):
        c = VectorCompressor(target_dim=32)
        cv = c.compress(np.arange(64, dtype=np.float64))
        restored = CompressedVector.from_dict(cv.to_dict())
        assert restored.payload == cv.payload
        assert restored.dims == cv.dims


class TestAgentMemoryOptimizationIntegration:
    """AgentMemorySystem.optimize_storage / recall_compressed (roadmap v10.17 → v11.3)."""

    def _make_system(self):
        from aios_core.agent_memory_system import AgentMemorySystem

        system = AgentMemorySystem()
        system._short_term.clear()
        return system

    def _seed(self, system):
        # Public record() path, then move entries to the pools the compressor indexes
        for platform, action, result, items in [
            ("olx", "collect", "success", 120),
            ("rozetka", "parse", "failure", 5),
            ("prom", "export", "success", 42),
        ]:
            system.record(platform=platform, action=action, result=result, context={"items": items})
        system._long_term.extend(system._short_term)
        system._short_term.clear()

    def test_optimize_storage_report(self):
        system = self._make_system()
        self._seed(system)
        report = system.optimize_storage(target_dim=64)
        assert report["entries_compressed"] == 3
        assert report["source_dim"] == 512
        assert report["ratio"] > 40
        assert report["compressed_bytes"] < report["original_bytes"]

    def test_recall_compressed_finds_matching_memory(self):
        system = self._make_system()
        self._seed(system)
        system.optimize_storage()
        results = system.recall_compressed("olx collect success", top_k=1)
        assert len(results) == 1
        assert results[0].platform == "olx"
        assert results[0].action == "collect"

    def test_recall_compressed_empty_memory(self):
        system = self._make_system()
        assert system.recall_compressed("anything") == []

    def test_stats_include_compression(self):
        system = self._make_system()
        self._seed(system)
        system.optimize_storage()
        stats = system.stats()
        assert "compression" in stats
        assert stats["compression"]["entries_compressed"] == 3
