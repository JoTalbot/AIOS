"""Tests for aios_core/transfer_learning.py"""
from __future__ import annotations
import pytest
from aios_core.transfer_learning import TransferLearning


@pytest.fixture()
def tl():
    return TransferLearning()


class TestTransferLearning:
    def test_create(self, tl):
        assert tl is not None

    def test_register_domain(self, tl):
        tl.register_domain(name="nlp", task_type="classification", data_size=10000)

    def test_get_domain(self, tl):
        tl.register_domain(name="cv", task_type="classification")
        d = tl.get_domain("cv")
        assert d is not None

    def test_store_knowledge(self, tl):
        tl.register_domain(name="domain1")
        tl.store_knowledge(domain="domain1", knowledge={"features": [1, 2, 3]})

    def test_get_knowledge(self, tl):
        tl.register_domain(name="domain1")
        tl.store_knowledge(domain="domain1", knowledge={"key": "val"})
        k = tl.get_knowledge("domain1")
        assert k is not None

    def test_domain_similarity(self, tl):
        tl.register_domain(name="src", task_type="classification")
        tl.register_domain(name="tgt", task_type="classification")
        sim = tl.domain_similarity(source="src", target="tgt")
        assert isinstance(sim, (int, float))

    def test_find_similar_domains(self, tl):
        tl.register_domain(name="a", task_type="classification")
        tl.register_domain(name="b", task_type="classification")
        tl.register_domain(name="target", task_type="classification")
        results = tl.find_similar_domains(target="target")
        assert isinstance(results, list)

    def test_is_negative_transfer(self, tl):
        tl.register_domain(name="src")
        tl.register_domain(name="tgt")
        result = tl.is_negative_transfer(source="src", target="tgt")
        assert isinstance(result, bool)

    def test_stats(self, tl):
        s = tl.stats()
        assert isinstance(s, dict)
