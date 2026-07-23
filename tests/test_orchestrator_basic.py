"""Tests for AIOS Orchestrator."""

import pytest
from aios_core.orchestrator import Task, TaskStep, TaskStatus, StepStatus, Orchestrator


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_task_status_values(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"


class TestStepStatus:
    """Tests for StepStatus enum."""

    def test_step_status_values(self):
        """Test StepStatus enum values."""
        assert StepStatus.PENDING == "pending"
        assert StepStatus.RUNNING == "running"
        assert StepStatus.COMPLETED == "completed"
        assert StepStatus.FAILED == "failed"
        assert StepStatus.SKIPPED == "skipped"


class TestTaskStep:
    """Tests for TaskStep class."""

    def test_task_step_creation(self):
        """Test creating a task step."""
        step = TaskStep(
            id="step-1",
            name="Test Step",
            description="Test description"
        )
        assert step.id == "step-1"
        assert step.name == "Test Step"
        assert step.description == "Test description"
        assert step.status == StepStatus.PENDING

    def test_task_step_with_parameters(self):
        """Test task step with parameters."""
        step = TaskStep(
            id="step-2",
            name="Parameterized Step",
            parameters={"key": "value"}
        )
        assert step.parameters == {"key": "value"}


class TestTask:
    """Tests for Task class."""

    def test_task_creation(self):
        """Test creating a task."""
        task = Task(
            id="task-1",
            name="Test Task",
            description="Test description"
        )
        assert task.id == "task-1"
        assert task.name == "Test Task"
        assert task.status == TaskStatus.PENDING
        assert len(task.steps) == 0

    def test_task_with_steps(self):
        """Test task with steps."""
        step1 = TaskStep(id="step-1", name="Step 1")
        step2 = TaskStep(id="step-2", name="Step 2")

        task = Task(
            id="task-2",
            name="Multi-step Task",
            steps=[step1, step2]
        )

        assert len(task.steps) == 2
        assert task.steps[0].id == "step-1"
        assert task.steps[1].id == "step-2"

    def test_task_status_transitions(self):
        """Test task status transitions."""
        task = Task(id="task-3", name="Status Test")

        # Initial status
        assert task.status == TaskStatus.PENDING

        # Transition to running
        task.status = TaskStatus.RUNNING
        assert task.status == TaskStatus.RUNNING

        # Transition to completed
        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED

    def test_task_to_dict(self):
        """Test task serialization."""
        step = TaskStep(id="step-1", name="Step 1")
        task = Task(
            id="task-4",
            name="Serialization Test",
            steps=[step]
        )

        task_dict = task.to_dict()

        assert task_dict["id"] == "task-4"
        assert task_dict["name"] == "Serialization Test"
        assert task_dict["status"] == TaskStatus.PENDING
        assert len(task_dict["steps"]) == 1


class TestOrchestrator:
    """Tests for Orchestrator class."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        return Orchestrator()

    def test_orchestrator_creation(self, orchestrator):
        """Test orchestrator creation."""
        assert orchestrator is not None

    def test_create_task(self, orchestrator):
        """Test creating a task through orchestrator."""
        task = orchestrator.create_task(
            task_id="task-1",
            name="Orchestrator Task",
            description="Created via orchestrator"
        )

        assert task is not None
        assert task.id == "task-1"
        assert task.name == "Orchestrator Task"

    def test_get_task(self, orchestrator):
        """Test getting a task."""
        # Create task
        orchestrator.create_task(
            task_id="task-2",
            name="Get Test"
        )

        # Get task
        task = orchestrator.get_task("task-2")
        assert task is not None
        assert task.id == "task-2"

    def test_list_tasks(self, orchestrator):
        """Test listing tasks."""
        # Create multiple tasks
        for i in range(5):
            orchestrator.create_task(
                task_id=f"task-{i}",
                name=f"Task {i}"
            )

        # List tasks
        tasks = orchestrator.list_tasks()
        assert len(tasks) >= 5

    def test_delete_task(self, orchestrator):
        """Test deleting a task."""
        # Create task
        orchestrator.create_task(
            task_id="task-delete",
            name="Delete Test"
        )

        # Delete task
        success = orchestrator.delete_task("task-delete")
        assert success

        # Verify deleted
        task = orchestrator.get_task("task-delete")
        assert task is None

    def test_get_nonexistent_task(self, orchestrator):
        """Test getting non-existent task."""
        task = orchestrator.get_task("nonexistent")
        assert task is None
