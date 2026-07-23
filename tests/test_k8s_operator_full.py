"""K8s operator full."""
from aios_core.k8s_operator import K8sOperator
def test(): s=K8sOperator().stats(); assert isinstance(s,dict)
