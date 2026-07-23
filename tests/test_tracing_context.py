from aios_core.tracing import Tracer
def test_context():
    t = Tracer()
    with t.span('op'): pass
    assert t.stats() is not None