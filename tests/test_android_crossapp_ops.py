"""Cross-app workflow ops."""
from aios_core.android_cross_app import WorkflowStatus, WorkflowStep
def test_status(): assert WorkflowStatus.PENDING.value == "pending"
def test_step(): s = WorkflowStep("com.app", "tap"); assert s.app_package == "com.app"
