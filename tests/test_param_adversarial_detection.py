import pytest
from aios_core.adversarial import AdversarialDefense

@pytest.mark.parametrize("data,threshold,expected", [
    ([0.0, 1.0], 0.3, True), ([0.1, 0.2], 0.3, False),
    ([0.0, 0.5, 1.0], 0.3, True), ([0.4, 0.5, 0.6], 0.3, False),
    ([], 0.3, False), ([0.0, 0.1], 0.01, True),
])
def test_detection(data, threshold, expected):
    ad = AdversarialDefense()
    assert ad.detect_adversarial(data, threshold) == expected
