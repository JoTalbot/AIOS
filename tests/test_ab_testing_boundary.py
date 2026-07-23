"""ab_testing boundary test."""
from aios_core.ab_testing import ABTest

def test_variant_exists(): assert ABTest('t',{'a':1.0}).assign_variant('u') == 'a'
