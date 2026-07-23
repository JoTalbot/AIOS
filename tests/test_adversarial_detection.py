from aios_core.adversarial import AdversarialDefense
def test_detection():
    ad = AdversarialDefense()
    assert ad.detect_adversarial([0.0, 1.0]) is True
    assert ad.detect_adversarial([0.1, 0.11]) is False