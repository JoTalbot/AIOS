"""Tests for AI Safety and Ethics Frameworks."""


from aios_core.ai_ethics import AIEthicsFramework
from aios_core.ai_safety import AISafetyFramework
from aios_core.ai_safety_benchmark import SafetyBenchmark
from aios_core.ai_safety_constitutional import ConstitutionalAI
from aios_core.ai_safety_dashboard import SafetyDashboard
from aios_core.ai_safety_evals import SafetyEvaluator
from aios_core.ai_safety_monitoring import SafetyMonitor


def test_ai_safety_framework():
    framework = AISafetyFramework()
    action = {"type": "execute_task", "description": "Process data batch"}
    res = framework.comprehensive_safety_check(action)

    assert isinstance(res, dict)
    assert "overall_safe" in res
    assert res["overall_safe"] is True
    assert framework.safety_checks_performed == 1


def test_ai_ethics_framework():
    ethics = AIEthicsFramework()
    action = {"type": "user_data_processing", "consent": True, "privacy_protected": True}
    res = ethics.evaluate_action(action)

    assert isinstance(res, dict)
    assert "overall_score" in res
    assert res["overall_score"] >= 0.0


def test_safety_monitor_and_alerts():
    monitor = SafetyMonitor()
    monitor.record_metric("harm_score", 0.1)
    assert len(monitor.alerts) == 0

    monitor.record_metric("harm_score", 0.8)  # Exceeds threshold 0.3
    assert len(monitor.alerts) == 1
    assert monitor.alerts[0]["metric"] == "harm_score"


def test_safety_dashboard():
    dashboard = SafetyDashboard()
    dashboard.update_metric("latency", 12.5)
    assert dashboard.safety_score == 1.0

    dashboard.add_incident({"severity": "high", "description": "Unusual command blocked"})
    assert dashboard.safety_score < 1.0
    status = dashboard.get_dashboard()
    assert len(status["recent_incidents"]) == 1


def test_safety_evals_and_benchmarks():
    evaluator = SafetyEvaluator()
    eval_res = evaluator.run_all("test_model")
    assert isinstance(eval_res, dict)
    assert len(eval_res) == 8

    c_ai = ConstitutionalAI()
    critique = c_ai.critique("Helpful answer")
    assert isinstance(critique, list)

    benchmark = SafetyBenchmark()
    bench_res = benchmark.run_benchmark("harmbench", None)
    assert isinstance(bench_res, dict)
