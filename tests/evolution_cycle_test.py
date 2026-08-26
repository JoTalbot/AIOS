def test_evolution_cycle():
    cycle = [
        "goal",
        "planning",
        "execution",
        "reflection",
        "learning",
        "evolution",
    ]

    assert len(cycle) == 6
    assert cycle[-1] == "evolution"
