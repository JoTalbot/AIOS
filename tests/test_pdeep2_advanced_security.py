"""Parametrized deep: advanced_security."""
import pytest
from aios_core.advanced_security import AdvancedSecurity
@pytest.mark.parametrize("ip,exp",[("0.0.0.0",True),("127.0.0.1",True),("8.8.8.8",False)])
def test_sec(ip,exp): assert AdvancedSecurity().detect_threat({"ip":ip})==exp

