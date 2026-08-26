from core.benchmark.system_benchmark import SystemBenchmark


def test_register_benchmark_result():
    benchmark = SystemBenchmark()
    benchmark.add_result("agent_quality", 0.9)

    assert benchmark.best_result().score == 0.9


def test_benchmark_history():
    benchmark = SystemBenchmark()
    benchmark.add_result("baseline", 0.5)
    benchmark.add_result("optimized", 0.8)

    assert len(benchmark.history()) == 2
