"""k8s_operator test."""
from aios_core.k8s_operator import K8sOperator
def test_init(): s = K8sOperator().stats(); assert isinstance(s, dict)
