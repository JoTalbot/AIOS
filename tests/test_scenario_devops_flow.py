"""DevOps full flow scenario."""
from aios_core.auto_scaler import AutoScaler
from aios_core.service_mesh import ServiceMesh
from aios_core.k8s_operator import K8sOperator
from aios_core.health_checks import HealthChecker
from aios_core.metrics_exporter import MetricsExporter
from aios_core.chaos import ChaosMonkey

def test_devops_stack():
    s = AutoScaler().stats(); assert isinstance(s, dict)
    s = ServiceMesh().stats(); assert isinstance(s, dict)
    s = K8sOperator().stats(); assert isinstance(s, dict)
    s = HealthChecker().stats(); assert isinstance(s, dict)
    s = MetricsExporter().stats(); assert isinstance(s, dict)
    s = ChaosMonkey().stats(); assert isinstance(s, dict)
