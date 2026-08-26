def test_workflow_controller_exists():
    from aios_v20.workflow.controller import AutonomousWorkflowController

    controller = AutonomousWorkflowController()
    state = controller.start('demo')

    assert state.status == 'RUNNING'
