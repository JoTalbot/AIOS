from aios_core.ab_testing import ABTest
def test_winner():
    ab = ABTest('test', {'a': 0.5, 'b': 0.5})
    ab.record_result('a', True); ab.record_result('a', True)
    ab.record_result('b', True)
    assert ab.get_winner() == 'a'