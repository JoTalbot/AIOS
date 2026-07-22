"""M8 Cross-App Workflow Engine tests"""

from aios_core.android_cross_app import CrossAppWorkflowEngine, WorkflowStatus

def test_create_workflow():
    engine = CrossAppWorkflowEngine()
    wf = engine.create_workflow("test", [
        {"app_package": "ua.slando", "action": "search", "params": {"query": "iPhone"}},
        {"app_package": "com.viber.voip", "action": "send_message", "params": {"message": "hi"}}
    ])
    assert wf.name == "test"
    assert len(wf.steps) == 2
    assert wf.status == WorkflowStatus.PENDING

def test_execute_simulated():
    engine = CrossAppWorkflowEngine()
    wf = engine.create_workflow("sim", [
        {"app_package": "ua.slando", "action": "search", "params": {"query": "iPhone"}, "output_key": "search_results"},
        {"app_package": "com.viber.voip", "action": "send_message", "params": {"message": "{{search_results.app}}"}, "critical": False}
    ])
    result = engine.execute(wf)
    assert result.status == WorkflowStatus.COMPLETED
    assert len(result.results) == 2
    assert result.duration_ms > 0

def test_param_templating():
    engine = CrossAppWorkflowEngine()
    wf = engine.create_workflow("tmpl", [
        {"app_package": "ua.slando", "action": "search", "params": {"query": "test"}, "output_key": "res"},
    ])
    wf.context = {"res": {"title": "iPhone 13"}}
    resolved = engine._resolve_params({"message": "Check {{res.title}}"}, wf.context)
    assert "iPhone 13" in resolved["message"]

def test_olx_to_messenger_workflow():
    engine = CrossAppWorkflowEngine()
    wf = engine.workflow_olx_to_messenger("iPhone", "+380123")
    assert len(wf.steps) == 3
    assert wf.steps[0].app_package == "ua.slando"

def test_broadcast_workflow():
    engine = CrossAppWorkflowEngine()
    wf = engine.workflow_multi_platform_broadcast("Hello", ["viber", "whatsapp"])
    assert len(wf.steps) == 2

def test_rollback_on_critical():
    def failing_factory(package):
        class FailDriver:
            def execute_action(self, pkg, action, params):
                return {"status": "error", "error": "fail"}
        return FailDriver()
    engine = CrossAppWorkflowEngine(driver_factory=failing_factory)
    wf = engine.create_workflow("fail", [
        {"app_package": "ua.slando", "action": "search", "params": {}, "critical": True}
    ])
    result = engine.execute(wf)
    assert result.status in (WorkflowStatus.FAILED, WorkflowStatus.ROLLED_BACK)
