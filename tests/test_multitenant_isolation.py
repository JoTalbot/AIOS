import pytest
from aios_core.multitenancy import MultiTenantManager
from aios_core.orchestrator import Orchestrator

def test_tenant_data_bounds():
    manager = MultiTenantManager()
    manager.create_tenant("tenant_a", "Alpha Corp")
    manager.create_tenant("tenant_b", "Beta Corp")
    
    # Simulate execution running under tenant_a
    exec_id = "task_123"
    manager.set_execution_context(exec_id, "tenant_a")
    
    # Tenant A accessing Tenant A data -> allowed
    assert manager.enforce_data_bound(exec_id, "tenant_a") is True
    
    # Tenant A accessing Tenant B data -> blocked
    with pytest.raises(PermissionError) as exc:
        manager.enforce_data_bound(exec_id, "tenant_b")
    
    assert "Data Isolation Breach" in str(exc.value)
    
    # System context (no bounded tenant) -> allowed
    sys_exec_id = "task_sys"
    assert manager.enforce_data_bound(sys_exec_id, "tenant_a") is True

def test_orchestrator_tenant_binding():
    orch = Orchestrator()
    orch.tenant_manager = MultiTenantManager()
    orch.tenant_manager.create_tenant("tenant_x", "X Corp")
    
    task = orch.create_task("fetch_data", tenant_id="tenant_x")
    assert task.metadata["tenant_id"] == "tenant_x"
    
    # Ensure executing the task automatically binds the context
    # (Since execute_task triggers evaluation and execution, we just check if it binds correctly initially)
    # We will patch the actual execute to fail fast just to see context bound
    
    original_exec = orch._execute_step
    bound_tenant = None
    
    def fake_exec(task_obj, step_obj):
        nonlocal bound_tenant
        bound_tenant = orch.tenant_manager.get_execution_context(task_obj.id)
        return True
        
    orch._execute_step = fake_exec
    orch.add_step(task, "fetch", params={})
    orch.execute_task(task)
    orch.tenant_manager.clear_execution_context(task.id) # Emulate finally block
    
    # Context should have been bound during execution
    assert bound_tenant == "tenant_x"
    
    # Context should be cleared after execution completes
    assert orch.tenant_manager.get_execution_context(task.id) is None
