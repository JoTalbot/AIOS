"""AB testing edge cases."""
from aios_core.ab_testing import ABTest
def test_full_weight(): assert ABTest("t",{"a":1.0}).assign_variant("u")=="a"
def test_no_results(): assert ABTest("t",{"a":0.5,"b":0.5}).stats()["results"]["a"]==0
