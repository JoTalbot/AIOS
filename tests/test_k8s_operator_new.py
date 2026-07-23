"""k8s_operator test."""
def test(): from aios_core.k8s_operator import K8sOperator; s = K8sOperator().stats(); assert isinstance(s, dict)
