"""Self healing edge cases."""
from aios_core.self_healing import SelfHealing
def test_unregistered(): assert SelfHealing().heal(ValueError()) is False
def test_registered(): sh=SelfHealing(); sh.register_strategy("KeyError", lambda c: None); assert sh.heal(KeyError()) is True
