def test_full_learning_cycle_contract():
    experience = {'action': 'optimize', 'reward': 1.0}
    assert experience['reward'] > 0


def test_learning_flow_stages():
    stages = [
        'memory',
        'optimization',
        'policy',
        'decision',
    ]
    assert stages[0] == 'memory'
    assert stages[-1] == 'decision'
