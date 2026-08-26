from aios.digital_twin.anomaly_detection import AnomalyDetector
from aios.digital_twin.behavior_model import BehaviorModel
from aios.digital_twin.forecasting import linear_forecast
from aios.digital_twin.autonomous_controller import AutonomousController


def test_anomaly_detection():
    assert AnomalyDetector(threshold=2).detect([1, 1, 10]) == [10]


def test_behavior_deviation():
    model = BehaviorModel()
    model.observe({"load": 10})
    assert model.deviation({"load": 13}) == {"load": 3}


def test_forecast():
    assert linear_forecast([10, 12], 2) == [14, 16]


def test_controller_requires_approval():
    controller = AutonomousController()
    controller.approve("scale")
    assert controller.plan("scale", {"nodes": 3})["action"] == "scale"
