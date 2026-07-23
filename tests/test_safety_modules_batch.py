"""Tests for AI Safety modules — batch coverage."""

from aios_core.agi_safety import AGISafety
from aios_core.ai_safety_amplification import IteratedAmplification
from aios_core.ai_safety_benchmark import SafetyBenchmark
from aios_core.ai_safety_deception import DeceptionDetector
from aios_core.ai_safety_evals import SafetyEvaluator
from aios_core.ai_safety_honesty import HonestyFramework
from aios_core.ai_safety_long_term import LongTermSafety
from aios_core.ai_safety_monitoring import SafetyMonitor
from aios_core.ai_safety_value_learning import ValueLearning
from aios_core.ai_scientist import AIScientist
from aios_core.ai_startup import AIStartup
from aios_core.benchmark import Benchmark
from aios_core.diffusion import DiffusionModel
from aios_core.circuit_breaker import CircuitBreaker


# AGI Safety
def test_agi_safety_stats():
    a = AGISafety()
    s = a.stats()
    assert isinstance(s, dict)


# Iterated Amplification
def test_amplification_stats():
    ia = IteratedAmplification()
    s = ia.stats()
    assert isinstance(s, dict)


# Safety Benchmark
def test_benchmark_stats():
    sb = SafetyBenchmark()
    s = sb.stats()
    assert isinstance(s, dict)


# Deception Detector
def test_deception_stats():
    dd = DeceptionDetector()
    s = dd.stats()
    assert isinstance(s, dict)


# Safety Evaluator
def test_evals_stats():
    se = SafetyEvaluator()
    s = se.stats()
    assert isinstance(s, dict)


# Honesty Framework
def test_honesty_stats():
    hf = HonestyFramework()
    s = hf.stats()
    assert isinstance(s, dict)


# Long Term Safety
def test_longterm_stats():
    lt = LongTermSafety()
    s = lt.stats()
    assert isinstance(s, dict)


# Safety Monitor
def test_monitor_stats():
    sm = SafetyMonitor()
    s = sm.stats()
    assert isinstance(s, dict)


# Value Learning
def test_value_learning_stats():
    vl = ValueLearning()
    s = vl.stats()
    assert isinstance(s, dict)


# AI Scientist
def test_scientist_stats():
    sc = AIScientist()
    s = sc.stats()
    assert isinstance(s, dict)


# AI Startup
def test_startup_stats():
    su = AIStartup()
    s = su.stats()
    assert isinstance(s, dict)


# Benchmark
def test_benchmark_runner():
    b = Benchmark()
    s = b.stats()
    assert isinstance(s, dict)


# Diffusion Model
def test_diffusion_stats():
    dm = DiffusionModel()
    s = dm.stats()
    assert isinstance(s, dict)


# Circuit Breaker (smoke)
def test_circuit_breaker_defaults():
    cb = CircuitBreaker()
    assert cb.state is not None
