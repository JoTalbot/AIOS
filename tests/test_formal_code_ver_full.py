"""Formal code verifier full."""
from aios_core.formal_code_verifier import FormalCodeVerifier
def test(): s=FormalCodeVerifier().stats(); assert isinstance(s,dict)
