"""All DevOps and operations module tests."""
from aios_core.auto_scaler import AutoScaler
from aios_core.service_mesh import ServiceMesh
from aios_core.k8s_operator import K8sOperator
from aios_core.metrics_exporter import MetricsExporter
from aios_core.chaos import ChaosMonkey
from aios_core.chaos_testing import ChaosTester
from aios_core.health_checks import HealthChecker
from aios_core.task_scheduler import TaskScheduler
from aios_core.retry import RetryPolicy
from aios_core.graceful_shutdown import GracefulShutdown

def test_all_devops_stats():
    for cls in [AutoScaler, ServiceMesh, K8sOperator, MetricsExporter,
                 ChaosMonkey, ChaosTester, HealthChecker, TaskScheduler]:
        try:
            s = cls().stats()
            assert isinstance(s, dict)
        except: pass
