"""Tests for Advanced ML Intelligence Layer (Milestone 4.2.1)."""


from aios_core.anomaly_detection import AnomalyDetector
from aios_core.autonomy_manager import AutonomyLevel
from aios_core.model_registry import ModelRegistry
from aios_core.model_serving import ModelServer
from aios_core.predictive_autonomy import PredictiveAutonomyRegulator


def test_model_registry():
    registry = ModelRegistry()

    # Register model
    entry = registry.register_model(
        name="risk_scorer",
        version="1.0.0",
        framework="onnx",
        metadata={"author": "AIOS Core Team"},
        artifact_bytes=b"mock_onnx_bytes",
    )

    assert entry["name"] == "risk_scorer"
    assert entry["stage"] == "staging"
    assert entry["sha256"] != "no_hash"

    # Promote to production
    promoted = registry.promote("risk_scorer", "1.0.0", stage="production")
    assert promoted is True

    # Retrieve production model
    prod_model = registry.get_model("risk_scorer", "production")
    assert prod_model is not None
    assert prod_model["version"] == "1.0.0"

    # Log metrics
    logged = registry.log_evaluation_metrics(
        "risk_scorer", "1.0.0", {"accuracy": 0.982, "f1": 0.975}
    )
    assert logged is True
    assert prod_model["eval_metrics"]["accuracy"] == 0.982


def test_model_server():
    server = ModelServer()

    # Deploy model endpoint v1
    v1_key = server.deploy("planner_evaluator", lambda x: x * 2, version="1.0.0", weight=1.0)
    assert v1_key == "planner_evaluator:1.0.0"

    # Perform prediction
    pred = server.predict("planner_evaluator", 21)
    assert pred["success"] is True
    assert pred["prediction"] == 42
    assert pred["version"] == "1.0.0"

    # Deploy v2 and configure A/B Split
    server.deploy("planner_evaluator", lambda x: x * 3, version="2.0.0", weight=1.0)
    server.set_traffic_split("planner_evaluator", {"1.0.0": 0.8, "2.0.0": 0.2})

    # Batch prediction
    batch_res = server.predict_batch("planner_evaluator", [10, 20, 30])
    assert len(batch_res) == 3
    for item in batch_res:
        assert item["success"] is True


def test_anomaly_detector():
    detector = AnomalyDetector(z_threshold=2.0)

    # Seed history with normal distribution around mean=100.0
    normal_data = [100.0, 102.0, 98.0, 101.0, 99.0, 100.5, 99.5, 101.2, 98.8, 100.1]
    for val in normal_data:
        assert detector.is_anomaly(val, metric_name="latency_ms") is False

    # Test extreme spike
    is_spike_anomalous = detector.is_anomaly(500.0, metric_name="latency_ms")
    assert is_spike_anomalous is True

    # Multivariate detection
    multi_res = detector.detect_multivariate({"memory_mb": 128.0, "error_rate": 0.01})
    assert "overall_anomaly" in multi_res


def test_predictive_autonomy_regulator():
    regulator = PredictiveAutonomyRegulator(high_risk_threshold=0.6, critical_risk_threshold=0.85)

    # Low risk step
    safe_step = {"action": "read_data", "complexity": 1.0}
    level, reason = regulator.regulate_autonomy(
        agent_id="agent_001", current_level=AutonomyLevel.LEVEL_5_SELF_DIRECTED, plan_step=safe_step
    )
    assert level == AutonomyLevel.LEVEL_5_SELF_DIRECTED

    # Critical risk step (destructive action)
    dangerous_step = {"action": "delete_all_database_records", "complexity": 10.0}
    regulated_level, _reason = regulator.regulate_autonomy(
        agent_id="agent_001",
        current_level=AutonomyLevel.LEVEL_5_SELF_DIRECTED,
        plan_step=dangerous_step,
        agent_history_stats={"failure_rate": 0.4},
    )

    # Must be downgraded to Level 1 Assisted
    assert regulated_level == AutonomyLevel.LEVEL_1_ASSISTED
    assert regulator.stats()["clamped_count"] == 1
