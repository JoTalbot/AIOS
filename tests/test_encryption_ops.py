from aios_core.encryption import EncryptionService
def test_ops():
    es = EncryptionService()
    assert es.stats() is not None