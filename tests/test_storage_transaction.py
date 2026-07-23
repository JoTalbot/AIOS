from aios_core.storage import Database
def test_transaction():
    db = Database(':memory:')
    assert db.stats()['dialect'] == 'sqlite'