from execution.persistence import ExecutionStore


def test_execution_store_persists_and_recovers_terminal_result():
    store = ExecutionStore()
    store.save_result("task-1", {"answer": "ok"})

    assert store.load_result("task-1") == {"answer": "ok"}


def test_execution_store_delete_is_idempotent():
    store = ExecutionStore()
    store.save_result("task-1", "ok")

    assert store.delete("task-1") is not None
    assert store.delete("task-1") is None
    assert store.load_result("task-1") is None
