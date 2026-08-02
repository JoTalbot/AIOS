"""
AIOS Code Orchestrator v3.1

This module coordinates AI-driven code generation and refactoring tasks.
Note: The 'todos' key in execution contexts is no longer used for task tracking.
All TODO processing has been centralized in aios_core/task_graph_executor.py
and aios_core/code_refactorer.py. This file now focuses solely on task orchestration.
"""

from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class CoderOrchestrator:
    """Orchestrates AI-driven code generation and refactoring tasks."""

    def __init__(self) -> None:
        """Initialize the orchestrator with clean state."""
        self._contexts: Dict[str, Dict[str, Any]] = {}
        # Initialize contexts without 'todos' to prevent legacy pollution
        self._active_tasks: List[str] = []

    def create_context(self, task_id: str, initial_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a clean execution context for a new task.

        Args:
            task_id: Unique identifier for the task
            initial_data: Optional initial context data (without 'todos')

        Returns:
            dict: Clean execution context
        """
        if initial_data is None:
            initial_data = {}

        # Ensure no legacy 'todos' key exists in the context
        clean_data = {k: v for k, v in initial_data.items() if k != "todos"}
        self._contexts[task_id] = clean_data
        return clean_data

    def update_context(self, task_id: str, updates: Dict[str, Any]) -> None:
        """Update task context with new data.

        Args:
            task_id: Task identifier
            updates: Dictionary of updates to apply

        Raises:
            ValueError: If task_id not found
        """
        if task_id not in self._contexts:
            raise ValueError(f"Task {task_id} not found")

        # Clean updates by removing any 'todos' entries
        clean_updates = {k: v for k, v in updates.items() if k != "todos"}
        self._contexts[task_id].update(clean_updates)

    def get_context(self, task_id: str) -> Dict[str, Any]:
        """Retrieve task context.

        Args:
            task_id: Task identifier

        Returns:
            dict: Task context

        Raises:
            ValueError: If task_id not found
        """
        if task_id not in self._contexts:
            raise ValueError(f"Task {task_id} not found")
        return self._contexts[task_id]

    def process_task_result(self, task_id: str, result: Dict[str, Any]) -> None:
        """Process the result of a task execution.

        Args:
            task_id: Task identifier
            result: Execution result containing task data

        Raises:
            ValueError: If task_id not found
        """
        if task_id not in self._contexts:
            raise ValueError(f"Task {task_id} not found")

        # Clean result by removing any 'todos' entries before merging
        clean_result = {k: v for k, v in result.items() if k != "todos"}
        self._contexts[task_id].update(clean_result)

    def cleanup_context(self, task_id: str) -> None:
        """Remove task context after completion.

        Args:
            task_id: Task identifier to cleanup

        Raises:
            ValueError: If task_id not found
        """
        if task_id not in self._contexts:
            raise ValueError(f"Task {task_id} not found")
        del self._contexts[task_id]

def orchestrate_task(
    orchestrator: CoderOrchestrator,
    task_id: str,
    initial_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Orchestrate a complete task lifecycle.

    Args:
        orchestrator: CoderOrchestrator instance
        task_id: Unique task identifier
        initial_context: Optional initial context

    Returns:
        dict: Final task context after orchestration
    """
    # Create clean context without legacy 'todos'
    context = orchestrator.create_context(task_id, initial_context)

    try:
        # Task processing would happen here
        # All TODO handling is delegated to specialized modules
        logger.info(f"Processing task {task_id} with clean context")

        # Example processing - in real implementation this would be AI-driven
        processed_data = {"status": "completed", "artifacts": []}

        # Update context with results (automatically cleaned)
        orchestrator.process_task_result(task_id, processed_data)

        return orchestrator.get_context(task_id)
    except Exception as e:
        logger.error(f"Task {task_id} failed: {str(e)}")
        raise

# Example usage
if __name__ == "__main__":
    orchestrator = CoderOrchestrator()
    result = orchestrate_task(orchestrator, "test-task-123")
    print(f"Task result: {result}")