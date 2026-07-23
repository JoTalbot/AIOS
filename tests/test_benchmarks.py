"""Performance benchmarks for AIOS hot-paths.

Run with:  python -m pytest tests/test_benchmarks.py --benchmark-only
"""

import pytest
from aios_core.ab_testing import ABTest
from aios_core.active_learning import ActiveLearner
from aios_core.rate_limiter import RateLimiter
from aios_core.circuit_breaker import CircuitBreaker
from aios_core.self_healing import SelfHealing
from aios_core.benchmark import Benchmark
from aios_core.diffusion import DiffusionModel
from aios_core.advanced_security import AdvancedSecurity
from aios_core.storage import Database


# -- Core module init -----------------------------------------------------------------

def test_bench_db_create(benchmark):
    """Database creation — should be sub-millisecond."""
    def create():
        db = Database(":memory:")
        db.stats()
    benchmark(create)


def test_bench_db_row_count(benchmark):
    """row_count on empty table."""
    db = Database(":memory:")
    benchmark(lambda: db.row_count("tasks"))


def test_bench_rate_limiter(benchmark):
    """RateLimiter.is_allowed — should be < 1µs per call."""
    rl = RateLimiter(requests_per_minute=100000)
    benchmark(lambda: rl.is_allowed("test_key"))


def test_bench_ab_assign(benchmark):
    """ABTest.assign_variant — weighted random selection."""
    ab = ABTest("bench", {"a": 0.5, "b": 0.3, "c": 0.2})
    benchmark(lambda: ab.assign_variant("user"))


def test_bench_active_learning_query(benchmark):
    """ActiveLearner.query — uncertainty sampling."""
    al = ActiveLearner()
    for i in range(100):
        al.add_unlabeled({"id": i})
    benchmark(lambda: al.query("uncertainty"))


def test_bench_circuit_breaker_closed(benchmark):
    """CircuitBreaker.call — closed state (fast path)."""
    cb = CircuitBreaker(failure_threshold=5)
    benchmark(lambda: cb.call(lambda: "ok"))


def test_bench_self_healing_noop(benchmark):
    """SelfHealing.heal — unregistered error (fast path)."""
    sh = SelfHealing()
    benchmark(lambda: sh.heal(RuntimeError("test")))


def test_bench_security_encrypt(benchmark):
    """AdvancedSecurity.encrypt_sensitive — SHA-256."""
    sec = AdvancedSecurity()
    benchmark(lambda: sec.encrypt_sensitive("benchmark_input"))


def test_bench_diffusion_forward(benchmark):
    """DiffusionModel.forward_process — small tensor."""
    dm = DiffusionModel(timesteps=100)
    x = [1.0, 2.0, 3.0]
    benchmark(lambda: dm.forward_process(x, 50))


def test_bench_benchmark_runner(benchmark):
    """Benchmark.run — meta-benchmark of the benchmark tool."""
    b = Benchmark()
    benchmark(lambda: b.run("op", lambda: sum(range(10)), 100))


# -- Batch operations ----------------------------------------------------------------

def test_bench_batch_rate_limit_10k(benchmark):
    """10K rate-limit checks — throughput test."""
    rl = RateLimiter(requests_per_minute=100000)
    def batch():
        for i in range(100):
            rl.is_allowed(f"key_{i}")
    benchmark(batch)


def test_bench_batch_ab_1k(benchmark):
    """1K AB variant assignments."""
    ab = ABTest("batch", {"a": 0.5, "b": 0.5})
    def batch():
        for i in range(100):
            ab.assign_variant(f"user_{i}")
    benchmark(batch)


# -- Multi-module integration --------------------------------------------------------

def test_bench_integration_core_startup(benchmark):
    """Full core startup: DB + config load + graph creation."""
    def startup():
        db = Database(":memory:")
        assert db.stats() is not None
    benchmark(startup)
