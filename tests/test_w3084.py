"""W-test 3084."""
from aios_core.auto_scaler import AutoScaler
from aios_core.service_mesh import ServiceMesh
from aios_core.k8s_operator import K8sOperator
from aios_core.health_checks import HealthChecker
from aios_core.metrics_exporter import MetricsExporter
from aios_core.chaos import ChaosMonkey
from aios_core.chaos_testing import ChaosTester

def test():
    for o in [AutoScaler(),ServiceMesh(),K8sOperator(),HealthChecker(),MetricsExporter(),ChaosMonkey(),ChaosTester()]:
        s = o.stats()
        assert s is not None
